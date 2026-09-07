import 'dart:async';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:just_audio/just_audio.dart';

/// Offline playback of bundled Punjabi/Urdu prompt audio AND of the
/// farmer's recorded answer files. Playback must never crash the farmer
/// flow.
///
/// Reliability fixes (M10 / "Listen Audio" button):
/// - a FRESH AudioPlayer per playback — reusing one player across repeated
///   stop/setAsset cycles left it in stale states that broke replays;
/// - `playAsset`/`playFile` await real completion (or error), so callers
///   always know when playback is done;
/// - `isPlaying` lets the UI toggle between play and stop.
///
/// Recording-safety fix:
/// - [stop] awaits full player disposal via [_playbackDone] so the
///   microphone is released before the recorder starts.  Without this,
///   unawaited dispose() left the audio session held and the recorder
///   captured silence or prompt-bleed (especially on Q3+).
class AudioService {
  AudioPlayer? _player;
  bool _playing = false;

  /// Resolves when the current _playImpl() finishes (including full
  /// player disposal).  stop() awaits this so callers know the audio
  /// hardware is released.
  Future<void>? _playbackDone;
  Completer<void>? _aborted;

  /// Called whenever [isPlaying] flips so the UI can rebuild and show
  /// the play/stop state while audio is actively playing.
  void Function()? onStateChanged;

  /// True while audio is actively playing.
  bool get isPlaying => _playing;

  void _setState(bool playing) {
    _playing = playing;
    onStateChanged?.call();
  }

  /// Plays a bundled asset and completes when playback finishes.
  Future<void> playAsset(String assetPath) => _play(() async {
    final player = _freshPlayer();
    await player.setAsset(assetPath);
    return player;
  });

  /// Plays a file from app temp storage (recorded answer) and completes
  /// when playback finishes.
  Future<void> playFile(String filePath) => _play(() async {
    final player = _freshPlayer();
    // Force a reload of the file by ensuring the player is fresh
    // and we are not reusing any URI-based caching in the OS.
    await player.setAudioSource(AudioSource.file(filePath), preload: false);
    return player;
  });

  AudioPlayer _freshPlayer() {
    final player = AudioPlayer();
    player.setVolume(1.0);
    return player;
  }

  /// Starts a playback session.  Awaits any previous session first so
  /// two playbacks never fight over the audio session.
  Future<void> _play(Future<AudioPlayer> Function() prepare) async {
    // Wait for any previous playback to fully finish (including
    // player disposal) before starting a new one.
    await _playbackDone;
    _playbackDone = _playImpl(prepare);
    await _playbackDone;
  }

  Future<void> _playImpl(Future<AudioPlayer> Function() prepare) async {
    _aborted = Completer<void>();
    AudioPlayer? player;
    try {
      player = await prepare();
      _player = player;
      _setState(true);
      // Race: real completion vs. stop() signalling us to abort.
      await Future.any([player.play(), _aborted!.future]);
    } catch (e) {
      // Audio must never break the farmer flow.
      debugPrint('[audio] playback failed: $e');
    } finally {
      _player = null;
      _setState(false);
      if (player != null) {
        try {
          await player.dispose();
        } catch (_) {}
      }
    }
  }

  /// Stops current playback and releases the player. Safe to call anytime.
  ///
  /// IMPORTANT: awaits full player disposal so the microphone / audio
  /// session is released before this future completes.  Callers (the
  /// recorder flow) rely on this to know the hardware is ready.
  Future<void> stop() async {
    final player = _player;
    _player = null;
    if (_playing) _setState(false);

    // Signal _playImpl to stop waiting for player.play().
    if (_aborted != null && !_aborted!.isCompleted) {
      _aborted!.complete();
    }

    // Wait for the full playback future (including player.dispose() in
    // the finally block) with a safety timeout.
    final done = _playbackDone;
    _playbackDone = null;
    if (done != null) {
      try {
        await done.timeout(const Duration(milliseconds: 500));
      } catch (_) {
        // Timeout – the player might leak but the flow must continue.
      }
    }

    // Belt-and-suspenders: if a player is still somehow alive,
    // force-stop and dispose it.
    if (player != null) {
      try {
        await player.stop();
        await player.dispose();
      } catch (_) {}
    }
  }

  Future<void> dispose() => stop();
}
