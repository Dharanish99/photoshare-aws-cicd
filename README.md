# PhotoShare AWS CI/CD Starter

This demo uses AWS CodePipeline (GitHub source), AWS CodeBuild (unittest), AWS Elastic Beanstalk (Python on AL2023 with ALB and EC2 Auto Scaling), and Amazon EFS (shared user uploads).

## Setup overview

1. Create GitHub repository and push these files to `main`.
2. Create AWS Elastic Beanstalk web environment using Python on Amazon Linux 2023; choose load-balanced environment, Application Load Balancer, min 1 max 2, public/default VPC, default/sample application to start.
3. Create AWS CodePipeline with GitHub via GitHub App source; CodeBuild build project using this `buildspec.yml`; Elastic Beanstalk deployment target. Connect CodeBuild output artifact to Deploy.
4. Once deployment works, create EFS in the EXACT SAME VPC as the Elastic Beanstalk EC2 instances; allow inbound TCP 2049 on EFS mount target security group from the EC2 instance security group only.
5. Set environment property `EFS_ID=fs-xxxxxxxxxxxxxxxxx` (plain text) under Elastic Beanstalk Configuration / Updates, monitoring, and logging / Environment properties. The `.platform/confighooks` script mounts EFS on a configuration deployment; `.platform/hooks` mounts it during application deployment and instance replacement.
6. Verify /health reports `Amazon EFS (shared)` and gallery saves a test image.
7. Change `VERSION = "v1"` in `application.py` to `VERSION = "v2"`, commit/push to main, and watch CodePipeline run tests and deploy the new version automatically.
8. For multi-instance shared storage demo, increase Elastic Beanstalk capacity minimum to 2, verify EC2 has two instances, and refresh webpage while photos remain present.
9. Delete Elastic Beanstalk environment, CodePipeline, CodeBuild project, independent EFS filesystem and security group, and unused S3 artifacts when finished to stop ongoing charges.

### Run locally

    python -m pip install -r requirements.txt
    python -m unittest discover -s tests -v
    python application.py

Visit http://127.0.0.1:5000/.

### Troubleshooting

- A 503 after setting EFS_ID means the EFS mount failed. Verify same VPC, available mount targets per Availability Zone, NFS TCP 2049 allowed from the exact EC2 instance security group, and inspect Elastic Beanstalk logs (`/var/log/eb-hooks.log` and `/var/log/eb-engine.log`).
- If the app displays `Local disk (setup only)`, EFS_ID is not set. Do not claim shared-storage validation yet.
- Initial demo mode stores files on each local instance separately: keep minimum instance count 1 until EFS is connected.
- Browser demo is intentionally unauthenticated HTTP for a temporary college lab. Do not upload sensitive information, and do not use it as a production photo service.
