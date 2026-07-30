#!/bin/bash
# Simple Octopus Skills Marketplace Installer
SKILL_NAME=$1
if [ -z "$SKILL_NAME" ]; then
  echo "Usage: $0 <skill-name>"
  exit 1
fi
echo "Installing skill: $SKILL_NAME (placeholder - copy SKILL.md manually or via git)"
