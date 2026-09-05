package com.example.fasal_guard_mobile

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.IOException
import java.util.concurrent.Executors

/// Unpacks the bundled ASR model (assets/flutter_assets/assets/asr_model/)
/// into app storage on a background thread. Streaming native copy keeps the
/// Flutter UI responsive and avoids holding the 365 MB in the Dart heap
/// (the pure-Dart rootBundle path froze the UI for ~74 s on the emulator).
class MainActivity : FlutterActivity() {
    private val executor = Executors.newSingleThreadExecutor()

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "fasal_guard/asr_model")
            .setMethodCallHandler { call, result ->
                if (call.method != "unpackAsset") {
                    result.notImplemented()
                    return@setMethodCallHandler
                }
                val asset = call.argument<String>("asset")
                val target = call.argument<String>("target")
                if (asset == null || target == null) {
                    result.error("bad-args", "asset/target required", null)
                    return@setMethodCallHandler
                }
                executor.execute {
                    try {
                        result.success(copyAsset(asset, target))
                    } catch (e: Exception) {
                        result.error("unpack-failed", e.message, null)
                    }
                }
            }
    }

    private fun copyAsset(assetPath: String, targetPath: String): Long {
        val target = File(targetPath)
        val tmp = File("$targetPath.part")
        assets.open(assetPath).use { input ->
            tmp.outputStream().use { out ->
                val buf = ByteArray(1024 * 1024)
                while (true) {
                    val n = input.read(buf)
                    if (n <= 0) break
                    out.write(buf, 0, n)
                }
                out.flush()
            }
        }
        if (!tmp.renameTo(target)) throw IOException("rename failed: $targetPath")
        return target.length()
    }
}
