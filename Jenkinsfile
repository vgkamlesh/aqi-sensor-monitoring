// Jenkins CI/CD pipeline for the AQI Sensor Network Health Monitoring project.
// Runs on every push: builds and tests the Java alerting service with
// Maven, then builds both Docker images to confirm they're deployable.
// Model training is NOT run here -- it's a slow, manual step (see
// src/train_model.py) that produces the checkpoint committed/stored
// separately; CI validates the code, not a multi-minute training job.

pipeline {
    agent any

    environment {
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build & Test Alerting Service (Maven)') {
            steps {
                dir('alerting') {
                    sh 'mvn -B clean test'
                }
            }
            post {
                always {
                    junit 'alerting/target/surefire-reports/*.xml'
                }
            }
        }

        stage('Package Alerting Jar') {
            steps {
                dir('alerting') {
                    sh 'mvn -B package -DskipTests'
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                sh 'docker build -t aqi-alerting:${IMAGE_TAG} -f alerting/Dockerfile alerting'
                sh 'docker build -t aqi-predictor:${IMAGE_TAG} -f docker/predictor.Dockerfile .'
            }
        }

        stage('Smoke Test: Compose Up') {
            steps {
                // Confirms the containers actually start together, not just
                // that they build. Requires processed_data/gat_gru_model.pt
                // to already exist on the Jenkins agent (training artifact,
                // not rebuilt by CI -- see note at top of file).
                sh 'docker compose up --build --abort-on-container-exit --exit-code-from alerting'
            }
        }
    }

    post {
        always {
            sh 'docker compose down || true'
        }
        success {
            echo 'Pipeline succeeded: tests passed, both images built, smoke test ran end-to-end.'
        }
        failure {
            echo 'Pipeline failed -- check the stage above for which step broke.'
        }
    }
}
