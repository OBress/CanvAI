"""
Create course_content.csv with full text from extracted_text folder
and link it to course_content_summary.csv via text_id
"""

import pandas as pd
from pathlib import Path
import csv


def collect_all_text_files(extracted_text_dir: Path):
    """
    Collect all text files from extracted_text that are NOT summary files.
    Returns list of (file_path, file_name) tuples.
    """
    text_files = []
    
    # Search all subdirectories
    for subfolder in extracted_text_dir.iterdir():
        if subfolder.is_dir() and subfolder.name != '__pycache__':
            print(f"Scanning {subfolder.name}...")
            
            for text_file in subfolder.glob('*.txt'):
                # Skip summary files
                if text_file.name.endswith('.summary.txt'):
                    continue
                
                text_files.append((text_file, text_file.name))
    
    return text_files


def create_course_content_csv(extracted_text_dir: Path, output_path: Path):
    """
    Create course_content.csv with id, file_name, and full_text columns.
    """
    print("="*80)
    print("CREATING COURSE_CONTENT.CSV")
    print("="*80)
    
    # Collect all text files
    text_files = collect_all_text_files(extracted_text_dir)
    print(f"\nFound {len(text_files)} text files (excluding summaries)")
    
    # Create CSV with streaming to handle large files
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id', 'file_name', 'full_text'])
        
        for idx, (file_path, file_name) in enumerate(text_files, start=1):
            if idx % 50 == 0:
                print(f"  Processed {idx}/{len(text_files)} files...")
            
            try:
                # Read full text
                full_text = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Write row
                writer.writerow([idx, file_name, full_text])
                
            except Exception as e:
                print(f"  Warning: Could not read {file_name}: {e}")
                writer.writerow([idx, file_name, f"ERROR: {e}"])
    
    print(f"\n[SUCCESS] Created {output_path}")
    print(f"  Total entries: {len(text_files)}")
    return text_files


def link_summaries_to_text(course_content_csv: Path, course_content_summary_csv: Path):
    """
    Add text_id column to course_content_summary.csv by matching summary files
    to their corresponding full text files.
    """
    print("\n" + "="*80)
    print("LINKING SUMMARIES TO FULL TEXT")
    print("="*80)
    
    # Load both CSVs
    print("Loading CSVs...")
    content_df = pd.read_csv(course_content_csv, encoding='utf-8')
    summary_df = pd.read_csv(course_content_summary_csv, encoding='utf-8')
    
    print(f"  course_content.csv: {len(content_df)} rows")
    print(f"  course_content_summary.csv: {len(summary_df)} rows")
    
    # Create a mapping from summary file name to text_id
    # For each file_name in course_content, the summary would be file_name + ".summary.txt"
    file_name_to_id = {}
    for _, row in content_df.iterrows():
        file_name = row['file_name']
        text_id = row['id']
        
        # The summary file would be this file_name + ".summary.txt"
        summary_file_name = file_name + ".summary.txt"
        file_name_to_id[summary_file_name] = text_id
    
    print(f"\nCreated mapping for {len(file_name_to_id)} text files")
    
    # Now match summaries in course_content_summary
    # The summary column contains the actual summary text, not the filename
    # So we need to match based on the files in extracted_text
    
    # Better approach: scan extracted_text for summary files and match their content
    project_root = Path(__file__).parent
    extracted_text_dir = project_root / 'extracted_text'
    
    # Build a mapping from summary text to text_id
    print("\nBuilding summary text to ID mapping...")
    summary_text_to_id = {}
    
    for subfolder in extracted_text_dir.iterdir():
        if subfolder.is_dir() and subfolder.name != '__pycache__':
            for summary_file in subfolder.glob('*.summary.txt'):
                try:
                    summary_text = summary_file.read_text(encoding='utf-8', errors='ignore').strip()
                    
                    # Get the corresponding text file name
                    text_file_name = summary_file.name.replace('.summary.txt', '')
                    
                    # Look up the ID
                    if text_file_name in content_df['file_name'].values:
                        text_id = content_df[content_df['file_name'] == text_file_name]['id'].iloc[0]
                        summary_text_to_id[summary_text] = text_id
                except Exception as e:
                    pass
    
    print(f"  Mapped {len(summary_text_to_id)} summaries to IDs")
    
    # Add text_id column to summary_df
    print("\nMatching summaries in course_content_summary.csv...")
    text_ids = []
    matched = 0
    
    for _, row in summary_df.iterrows():
        summary = row.get('summary', 'N/A')
        
        if summary != 'N/A' and summary in summary_text_to_id:
            text_ids.append(summary_text_to_id[summary])
            matched += 1
        else:
            text_ids.append('N/A')
    
    summary_df['text_id'] = text_ids
    
    print(f"  Matched {matched} summaries to full text IDs")
    print(f"  Unmatched: {len(summary_df) - matched}")
    
    # Save updated course_content_summary.csv
    summary_df.to_csv(course_content_summary_csv, index=False, encoding='utf-8')
    print(f"\n[SUCCESS] Updated {course_content_summary_csv}")
    print(f"  Added 'text_id' column")
    
    return summary_df


def main():
    """Main function"""
    project_root = Path(__file__).parent
    extracted_text_dir = project_root / 'extracted_text'
    data_dir = project_root / 'data'
    
    course_content_csv = data_dir / 'course_content.csv'
    course_content_summary_csv = data_dir / 'course_content_summary.csv'
    
    if not extracted_text_dir.exists():
        print(f"Error: {extracted_text_dir} not found")
        return
    
    if not course_content_summary_csv.exists():
        print(f"Error: {course_content_summary_csv} not found")
        return
    
    # Step 1: Create course_content.csv
    text_files = create_course_content_csv(extracted_text_dir, course_content_csv)
    
    # Step 2: Link summaries to text IDs
    link_summaries_to_text(course_content_csv, course_content_summary_csv)
    
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"Created: {course_content_csv}")
    print(f"Updated: {course_content_summary_csv} (added text_id column)")
    print("="*80)


if __name__ == "__main__":
    main()

