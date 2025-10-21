#!/bin/sh

set -e

uv run celery -A src.background.celery_app.celery_app worker -B -l info
