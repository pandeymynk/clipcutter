import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

// Same version as the desktop app (pyproject.toml), overridable from CI.
val appVersion: String = System.getenv("CLIPCUTTER_VERSION")
    ?: rootProject.file("../pyproject.toml").readLines()
        .first { it.startsWith("version") }.substringAfter('"').substringBefore('"')

// Release signing: CI writes android/keystore.properties from secrets; without it the release APK is
// signed with the debug key (fine for sideloading, not for the Play Store).
val keystoreProps = Properties().apply {
    val f = rootProject.file("keystore.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    namespace = "app.clipcutter.android"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.clipcutter.android"
        minSdk = 29            // Android 10
        targetSdk = 35
        versionName = appVersion
        versionCode = appVersion.split(".").map { it.toIntOrNull() ?: 0 }
            .let { (it + listOf(0, 0, 0)).take(3) }.let { it[0] * 10000 + it[1] * 100 + it[2] }
        ndk { abiFilters += listOf("arm64-v8a") }   // the tools in jniLibs are arm64-only
    }

    signingConfigs {
        if (keystoreProps.isNotEmpty()) {
            create("release") {
                storeFile = rootProject.file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("debug")
        }
    }

    packaging {
        // ffmpeg, ffprobe, qjs and whisper-cli ship as lib*.so and must be extracted to disk so they can be exec'd
        jniLibs { useLegacyPackaging = true }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        System.getenv("CLIPCUTTER_BUILD_PYTHON")?.let { buildPython(it) }
        pip {
            // prebuilt Android wheels from Chaquopy's repo (numpy 2.x / OpenCV aren't built for Android 3.13 yet)
            install("numpy==1.26.2")
            install("pillow==11.0.0")
            install("pyyaml==6.0.3")
            install("certifi")
            install("yt-dlp")
            install("yt-dlp-ejs")      // YouTube's JS challenge solver scripts (run by qjs)
        }
    }
    sourceSets {
        getByName("main") {
            srcDir("../../src")         // the same clipcutter package the desktop app uses
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
}
