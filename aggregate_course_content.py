"""
Aggregate all CSV files from data/new_data into a single course_content_summary.csv
with summaries extracted from the extracted_text folder.
"""

import pandas as pd
import re
from pathlib import Path
from typing import Optional


def extract_course_name(filename: str) -> str:
    """
    Extract clean course name from filename.
    Example: 'files_10500000002426582_cmpsc461_fa25_sections_003_004_programming_language_concepts.csv'
    Returns: 'CMPSC461 FA25 Programming Language Concepts'
    """
    # Remove file type prefix and course ID
    name = re.sub(r'^(files|assignments|modules|module_items|pages|quizzes)_\d+_', '', filename)
    # Remove .csv extension
    name = name.replace('.csv', '')
    # Remove trailing fluff like section numbers
    name = re.sub(r'_sections?_\d+_\d+', '', name)
    name = re.sub(r'_\d+_up_p_\w+_\d+', '', name)
    
    # Convert underscores to spaces and title case
    name = name.replace('_', ' ').title()
    
    # Clean up common patterns
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'Sec \d+ And \d+', '', name)
    
    return name.strip()


def find_summary_file(course_id: str, course_name_raw: str, display_name: str, content_type: str, extracted_text_dir: Path) -> Optional[str]:
    """
    Find and read the summary file for a given file entry.
    Returns the summary text or None if not found.
    """
    if not display_name or pd.isna(display_name):
        return None
    
    # Determine subfolder based on content type
    type_mapping = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        'application/vnd.ms-powerpoint': 'pptx',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'docx',
        'text/plain': 'txt',
        'application/zip': 'zip',
        'application/x-zip-compressed': 'zip'
    }
    
    subfolder = type_mapping.get(content_type)
    if not subfolder:
        return None
    
    # Construct expected summary file pattern
    # Pattern: files_<course_id>_<course_name>__<display_name>.<ext>.txt.summary.txt
    search_dir = extracted_text_dir / subfolder
    if not search_dir.exists():
        return None
    
    # Find file matching display_name
    # The file will have format: files_<course_id>_<course_name_normalized>__<display_name>.txt.summary.txt
    for summary_file in search_dir.glob('*.summary.txt'):
        # Check if the display name appears in the file
        if display_name.replace(' ', '_') in summary_file.name or \
           display_name.replace(' ', '') in summary_file.name:
            try:
                return summary_file.read_text(encoding='utf-8', errors='ignore').strip()
            except Exception as e:
                print(f"  Warning: Could not read summary file {summary_file.name}: {e}")
                return None
    
    return None


def process_files_csv(csv_path: Path, course_name: str, extracted_text_dir: Path) -> pd.DataFrame:
    """Process files_*.csv files"""
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    result_rows = []
    for _, row in df.iterrows():
        summary = find_summary_file(
            str(row.get('id', '')),
            csv_path.stem,
            row.get('display_name', ''),
            row.get('content-type', ''),
            extracted_text_dir
        )
        
        result_rows.append({
            'canvas_id': row.get('id'),
            'course_name': course_name,
            'type': 'file',
            'title': row.get('display_name', ''),
            'date': row.get('modified_at', row.get('created_at', '')),
            'link': row.get('url', ''),
            'is_completed': 'N/A',
            'grade': 'N/A',
            'summary': summary if summary else 'N/A'
        })
    
    return pd.DataFrame(result_rows)


def process_assignments_csv(csv_path: Path, course_name: str) -> pd.DataFrame:
    """Process assignments_*.csv files"""
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    result_rows = []
    for _, row in df.iterrows():
        result_rows.append({
            'canvas_id': row.get('id'),
            'course_name': course_name,
            'type': 'assignment',
            'title': row.get('name', ''),
            'date': row.get('due_at', row.get('created_at', '')),
            'link': row.get('html_url', ''),
            'is_completed': 'N/A',  # Would need submission data
            'grade': row.get('points_possible', 'N/A'),
            'summary': 'N/A'
        })
    
    return pd.DataFrame(result_rows)


def process_modules_csv(csv_path: Path, course_name: str) -> pd.DataFrame:
    """Process modules_*.csv files"""
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    result_rows = []
    for _, row in df.iterrows():
        result_rows.append({
            'canvas_id': row.get('id'),
            'course_name': course_name,
            'type': 'module',
            'title': row.get('name', ''),
            'date': row.get('publish_at', ''),
            'link': 'N/A',
            'is_completed': row.get('state', 'N/A'),
            'grade': 'N/A',
            'summary': 'N/A'
        })
    
    return pd.DataFrame(result_rows)


def process_module_items_csv(csv_path: Path, course_name: str) -> pd.DataFrame:
    """Process module_items_*.csv files"""
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    result_rows = []
    for _, row in df.iterrows():
        result_rows.append({
            'canvas_id': row.get('id'),
            'course_name': course_name,
            'type': row.get('type', 'module_item'),
            'title': row.get('title', ''),
            'date': row.get('publish_at', ''),
            'link': row.get('html_url', row.get('external_url', 'N/A')),
            'is_completed': row.get('completed_at') if pd.notna(row.get('completed_at')) else 'N/A',
            'grade': 'N/A',
            'summary': 'N/A'
        })
    
    return pd.DataFrame(result_rows)


def process_pages_csv(csv_path: Path, course_name: str) -> pd.DataFrame:
    """Process pages_*.csv files"""
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    result_rows = []
    for _, row in df.iterrows():
        result_rows.append({
            'canvas_id': row.get('page_id'),
            'course_name': course_name,
            'type': 'page',
            'title': row.get('title', ''),
            'date': row.get('updated_at', row.get('created_at', '')),
            'link': row.get('html_url', ''),
            'is_completed': 'N/A',
            'grade': 'N/A',
            'summary': 'N/A'
        })
    
    return pd.DataFrame(result_rows)


def process_quizzes_csv(csv_path: Path, course_name: str) -> pd.DataFrame:
    """Process quizzes_*.csv files"""
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    result_rows = []
    for _, row in df.iterrows():
        result_rows.append({
            'canvas_id': row.get('id'),
            'course_name': course_name,
            'type': 'quiz',
            'title': row.get('title', ''),
            'date': row.get('due_at', ''),
            'link': row.get('html_url', ''),
            'is_completed': 'N/A',
            'grade': row.get('points_possible', 'N/A'),
            'summary': 'N/A'
        })
    
    return pd.DataFrame(result_rows)


def main():
    """Main aggregation function"""
    print("="*80)
    print("COURSE CONTENT AGGREGATION")
    print("="*80)
    
    # Setup paths
    project_root = Path(__file__).parent
    new_data_dir = project_root / 'data' / 'new_data'
    extracted_text_dir = project_root / 'extracted_text'
    output_path = project_root / 'data' / 'course_content_summary.csv'
    
    if not new_data_dir.exists():
        print(f"Error: Directory not found: {new_data_dir}")
        return
    
    # Process all CSV files
    all_data = []
    csv_files = list(new_data_dir.glob('*.csv'))
    print(f"\nFound {len(csv_files)} CSV files to process\n")
    
    for csv_file in csv_files:
        print(f"Processing: {csv_file.name}")
        course_name = extract_course_name(csv_file.name)
        print(f"  Course: {course_name}")
        
        try:
            if csv_file.name.startswith('files_'):
                df = process_files_csv(csv_file, course_name, extracted_text_dir)
            elif csv_file.name.startswith('assignments_'):
                df = process_assignments_csv(csv_file, course_name)
            elif csv_file.name.startswith('modules_') and not csv_file.name.startswith('module_items_'):
                df = process_modules_csv(csv_file, course_name)
            elif csv_file.name.startswith('module_items_'):
                df = process_module_items_csv(csv_file, course_name)
            elif csv_file.name.startswith('pages_'):
                df = process_pages_csv(csv_file, course_name)
            elif csv_file.name.startswith('quizzes_'):
                df = process_quizzes_csv(csv_file, course_name)
            else:
                print(f"  Skipped: Unknown file type")
                continue
            
            all_data.append(df)
            print(f"  Added {len(df)} rows")
            
        except Exception as e:
            print(f"  Error processing {csv_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Save to output
        combined_df.to_csv(output_path, index=False, encoding='utf-8')
        
        print("\n" + "="*80)
        print(f"SUCCESS: Created {output_path}")
        print(f"Total rows: {len(combined_df)}")
        print(f"Columns: {', '.join(combined_df.columns)}")
        print("="*80)
        
        # Print summary stats
        print("\nSummary by type:")
        print(combined_df['type'].value_counts())
        print("\nSummary by course:")
        print(combined_df['course_name'].value_counts())
        print("\nRows with summaries:", (combined_df['summary'] != 'N/A').sum())
        
    else:
        print("\nNo data processed!")


if __name__ == "__main__":
    main()

