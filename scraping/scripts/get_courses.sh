#!/bin/bash
# initially get all courses

mkdir -p data
curl -o data/courses.json "https://canvas.instructure.com/api/v1/courses?access_token=1050~TFyrBRE8N4v9BxVJGQ3DeCDvhxh749hUE4zc9YTBRhK8ZLTuMN2FKEVzEVKYeXY2"
