allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// tflite_flutter/speech_to_text ship older Java targets but Kotlin 17;
// their build.gradle files are patched to VERSION_17 by
// scripts/patch_plugin_jvm_targets.py (idempotent, run after pub get).

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
