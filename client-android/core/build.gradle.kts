plugins {
    id("org.jetbrains.kotlin.jvm")
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    testClassesDirs = files(layout.buildDirectory.dir("classes/kotlin/test"))
    classpath = classpath + files(
        layout.buildDirectory.dir("classes/kotlin/main"),
        layout.buildDirectory.dir("classes/kotlin/test"),
    )
}
