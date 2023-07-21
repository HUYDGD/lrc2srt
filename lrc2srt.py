import os
import re

def parse_lrc_timestamp(timestamp):
    try:
        minutes, seconds = timestamp.split(':')
        seconds, milliseconds = seconds.split('.')
        minutes, seconds, milliseconds = int(minutes), int(seconds), int(milliseconds)
        return minutes * 60 + seconds + milliseconds / 100
    except ValueError:
        return None

def lrc_to_srt(lrc_file_path, srt_file_path):
    with open(lrc_file_path, 'r', encoding='utf-8') as lrc_file:
        lrc_content = lrc_file.read()

    subs = []
    pattern = r'\[(\d+:\d+\.\d+)\](.*)'
    matches = re.findall(pattern, lrc_content)
    for idx, match in enumerate(matches):
        timestamp, text = match
        start_time = parse_lrc_timestamp(timestamp)
        if start_time is not None:
            end_time = parse_lrc_timestamp(matches[idx + 1][0]) if idx + 1 < len(matches) else start_time + 1
            subs.append(f"{len(subs) + 1}\n{format_time(start_time)} --> {format_time(end_time)}\n{text.strip()}\n")

    with open(srt_file_path, 'w', encoding='utf-8') as srt_file:
        srt_file.writelines(subs)

def format_time(seconds):
    hours = int(seconds) // 3600
    minutes = (int(seconds) % 3600) // 60
    seconds = int(seconds) % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

if __name__ == "__main__":
    # Prompt the user to enter the directory path
    directory = input("Enter the directory path where the .lrc files are located: ")

    # Validate the directory path
    while not os.path.isdir(directory):
        print("Invalid directory path. Please try again.")
        directory = input("Enter the directory path where the .lrc files are located: ")

    # Get a list of all .lrc files in the directory
    lrc_files = [file for file in os.listdir(directory) if file.endswith('.lrc')]

    # Loop through each .lrc file and convert it to .srt
    for lrc_file in lrc_files:
        # Generate the corresponding .srt filename
        srt_file = os.path.splitext(lrc_file)[0] + '.srt'

        # Convert .lrc to .srt
        lrc_to_srt(os.path.join(directory, lrc_file), os.path.join(directory, srt_file))

        print(f"Converted '{lrc_file}' to '{srt_file}'")

    print("Conversion complete!")
