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
class AudioService {
  AudioPlayer? _player;
  bool _playing = false;

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
        await player.setFilePath(filePath);
        return player;
      });

  AudioPlayer _freshPlayer() {
    final player = AudioPlayer();
    player.setVolume(1.0);
    return player;
  }

  Future<void> _play(Future<AudioPlayer> Function() prepare) async {
    await stop();
    AudioPlayer? player;
    try {
      player = await prepare();
      _player = player;
      _setState(true);
      // just_audio's play() completes when playback ends or is stopped.
      await player.play();
    } catch (e) {
      // Audio must never break the farmer flow.
      debugPrint('[audio] playback failed: $e');
    } finally {
      if (_player == player) {
        _setState(false);
      }
    }
  }

  /// Stops current playback and releases the player. Safe to call anytime.
  Future<void> stop() async {
    final player = _player;
    _player = null;
    if (_playing) _setState(false);
    if (player == null) return;
    try {
      await player.stop();
      await player.dispose();
    } catch (_) {
      // Stopping must never throw into the farmer flow.
    }
  }

  Future<void> dispose() => stop();
}
