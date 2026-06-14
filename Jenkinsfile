/*
 * ShopMiner Jenkins CI Pipeline
 * =============================
 * Declarative pipeline for continuous integration.
 * Triggers: SCM polling (fallback) or Gitee webhook (recommended).
 *
 * Prerequisites (Jenkins Plugins):
 *   - Pipeline
 *   - Allure Jenkins Plugin
 *   - NodeJS Plugin (with Node.js 18+ installed)
 *   - Gitee Plugin (optional, for webhook triggers)
 *
 * Environment variables expected (set in Jenkins → Manage Jenkins → Configure System):
 *   - (none required; all defaults derived from workspace)
 */

pipeline {
    agent any

    triggers {
        // SCM polling every 5 minutes as fallback.
        // For real-time triggers, configure Gitee Webhook instead
        // (see docs/ci/jenkins-setup.md for instructions).
        pollSCM('H/5 * * * *')
    }

    environment {
        // ---------- Python virtual environment ----------
        VENV_DIR     = "${WORKSPACE}/.venv"
        PIP_CACHE    = "${WORKSPACE}/.pip-cache"

        // ---------- Test & report paths ----------
        ALLURE_DIR   = "${WORKSPACE}/tests/report/allure-results"
        REPORTS_DIR  = "${WORKSPACE}/reports"
        COVERAGE_DIR = "${REPORTS_DIR}/coverage-html"

        // ---------- Node.js configuration ----------
        // Requires NodeJS plugin with a global tool named "NodeJS 18+"
        NODEJS_HOME  = tool name: 'NodeJS 18+', type: 'nodejs'
        PATH         = "${NODEJS_HOME}/bin:${VENV_DIR}/bin:${env.PATH}"
    }

    stages {
        // -------------------------------------------------------
        // Stage 1: Checkout
        // -------------------------------------------------------
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // -------------------------------------------------------
        // Stage 2: Install Backend Dependencies
        // -------------------------------------------------------
        stage('Install Backend') {
            steps {
                sh """
                    # Create Python virtual environment
                    python3 -m venv "${VENV_DIR}"

                    # Activate & upgrade pip
                    . "${VENV_DIR}/bin/activate"
                    pip install --upgrade pip

                    # Install project dependencies
                    pip install -r requirements.txt
                """
            }
        }

        // -------------------------------------------------------
        // Stage 3: Install Frontend Dependencies
        // -------------------------------------------------------
        stage('Install Frontend') {
            steps {
                sh '''
                    cd frontend
                    npm ci
                '''
            }
        }

        // -------------------------------------------------------
        // Stage 4: Run Backend Tests (unit + API)
        // -------------------------------------------------------
        stage('Run Backend Tests') {
            steps {
                sh """
                    . "${VENV_DIR}/bin/activate"
                    mkdir -p "${REPORTS_DIR}"
                    pytest tests/unit/ tests/api/ -v \
                        --alluredir="${ALLURE_DIR}" \
                        --junitxml="${REPORTS_DIR}/junit-backend.xml"
                """
            }
        }

        // -------------------------------------------------------
        // Stage 5: Test Coverage Report
        // -------------------------------------------------------
        stage('Coverage') {
            steps {
                sh """
                    . "${VENV_DIR}/bin/activate"
                    mkdir -p "${COVERAGE_DIR}"
                    pytest --cov=app --cov-report=html:"${COVERAGE_DIR}" --cov-report=term
                """
            }
            post {
                success {
                    // Archive HTML coverage report so it's accessible from Jenkins UI
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: "${COVERAGE_DIR}",
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
            }
        }

        // -------------------------------------------------------
        // Stage 6: Frontend Unit Tests
        // -------------------------------------------------------
        stage('Frontend Tests') {
            steps {
                sh '''
                    cd frontend
                    mkdir -p "${WORKSPACE}/reports"
                    npx vitest run \
                        --reporter=junit \
                        --outputFile="${WORKSPACE}/reports/junit-frontend.xml"
                '''
            }
        }

        // -------------------------------------------------------
        // Stage 7: Allure Report
        // -------------------------------------------------------
        stage('Allure Report') {
            steps {
                allure includeProperties: false,
                        results: [[path: "${ALLURE_DIR}"]]
            }
        }

        // -------------------------------------------------------
        // Stage 8: Docker Build
        // -------------------------------------------------------
        stage('Docker Build') {
            steps {
                sh 'docker-compose build'
            }
        }
    }

    post {
        // ------------------------------------------------------------------
        // Always collect test results, even when the build fails.
        // ------------------------------------------------------------------
        always {
            junit 'reports/junit-*.xml'
            cleanWs()
        }

        // ------------------------------------------------------------------
        // On failure: mark build with appropriate messages.
        // Customize with email/Slack/WeCom notifications as needed.
        // ------------------------------------------------------------------
        failure {
            echo '❌ Pipeline failed. Check the stage logs above for details.'
        }

        unstable {
            echo '⚠️  Pipeline completed with unstable (test failures).'
        }

        success {
            echo '✅ Pipeline completed successfully.'
        }
    }
}
