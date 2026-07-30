import os
import sys

def summarize(logs_dir):
    output_file = 'summary.txt'
    with open(output_file, 'w') as out:
        for f in os.listdir(logs_dir):
            if f.endswith('.md'):
                with open(os.path.join(logs_dir, f), 'r', errors='ignore') as log:
                    for line in log:
                        if line.strip().startswith('- '):
                            out.write(line)
    print(f'Summary created: {output_file}')

if __name__ == '__main__':
    logs_path = sys.argv[1] if len(sys.argv) > 1 else '.'
    summarize(logs_path)
