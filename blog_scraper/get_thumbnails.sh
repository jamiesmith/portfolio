#!/bin/bash

INPUT_FILE="blog_summaries.csv"
OUTPUT_DIR="thumbnails"

# Make output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Skip header row, extract the Thumbnail column, and download each image
tail -n +2 "$INPUT_FILE" | while IFS=, read -r title date url thumbnail summary; do
    # Clean thumbnail URL (remove quotes if CSV added them)
    thumb_url=$(echo "$thumbnail" | tr -d '"')

    if [[ -n "$thumb_url" && "$thumb_url" != "None" ]]; then
        # Create a safe filename from the title
        safe_title=$(echo "$title" | tr -cd '[:alnum:]_-')
        file_ext="${thumb_url##*.}"
        file_ext="${file_ext%%\?*}"  # Remove query params if any
        output_path="$OUTPUT_DIR/${safe_title}.${file_ext}"

        echo "Downloading: [$thumb_url] -> $output_path"
        curl -sL "$thumb_url" -o "$output_path"
	sleep 2
    fi
done
