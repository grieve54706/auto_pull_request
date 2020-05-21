pipeline {
    environment {
        BITBUCKET_CREDS = credentials("${params.Bitbucket}")
    }
    agent any
    options { 
        timestamps() 
    }
    stages {
        stage('Prepare python env') {
            steps {
                dir("auto_pull_request") {
                    script {
                        if (!fileExists('.env')) {
                            echo 'Creating virtualenv ...'
                            sh 'virtualenv .env'
                        }
                        sh """
                        source .env/bin/activate
                        pip install -r requirements.txt
                        """
                    }
                }
            }
        }
        stage('Create pull request') {
            parallel {
                stage('microservice') {
                    steps {
                        sh """
                        cd auto_pull_request
                        python auto_pr.py microservice
                        """
                    }
                }
                stage('frontend-ib') {
                    steps {
                        sh """
                        cd auto_pull_request
                        python auto_pr.py frontend-ib
                        """
                    }
                }
                stage('web-ui') {
                    steps {
                        sh """
                        cd auto_pull_request
                        python auto_pr.py web-ui
                        """
                    }
                }
            }
        }
    }
}