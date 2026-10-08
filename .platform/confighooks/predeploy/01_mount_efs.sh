#!/bin/bash
# Runs automatically on every code deployment and on replacement EC2 instances.
set -euo pipefail
EFS_ID="$(/opt/elasticbeanstalk/bin/get-config environment -k EFS_ID 2>/dev/null || true)"
if [[ -z "$EFS_ID" || "$EFS_ID" == "null" ]]; then
  echo "PhotoShare: EFS_ID is not configured. Staying in temporary local-storage mode."
  exit 0
fi
mkdir -p /mnt/efs
if ! mountpoint -q /mnt/efs; then
  dnf -y install amazon-efs-utils
  mount -t efs -o tls "${EFS_ID}:/" /mnt/efs
fi
install -d -m 775 -o webapp -g webapp /mnt/efs/photos
echo "PhotoShare: mounted $EFS_ID at /mnt/efs; photos shared via /mnt/efs/photos"
