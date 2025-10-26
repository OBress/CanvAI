#!/usr/bin/env python3
"""
CSV Formatter Script

This script formats various CSV files and text files into 5 core CSV files:
1. course_content_summary.csv
2. courses.csv  
3. users.csv
4. grades.csv
5. course_content.csv

The script processes assignments, files, module_items, modules, pages, and quizzes CSV files
and combines them into the course_content_summary.csv. It also extracts text content
from the extracted_text folder and creates the course_content.csv with unique IDs.
"""

import os
import csv
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVFormatter:
    def __init__(self, data_dir: str = "data", extracted_text_dir: str = "extracted_text", output_dir: str = "data/formatted"):
        # Get the project root directory (two levels up from this script)
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        
        self.data_dir = project_root / data_dir
        self.extracted_text_dir = project_root / extracted_text_dir
        self.output_dir = project_root / output_dir
        self.text_id_counter = 1
        self.course_content_data = []
        self.course_content_summary_data = []
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_course_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract course ID from filename pattern like 'assignments_10500000002349828_...'"""
        match = re.search(r'(\d{17})', filename)
        return match.group(1) if match else None
    
    def extract_course_name_from_filename(self, filename: str) -> Optional[str]:
        """Extract course name from filename pattern"""
        # Remove the prefix and course ID, then clean up the name
        parts = filename.split('_')
        if len(parts) >= 3:
            # Skip the first part (type) and second part (course_id)
            course_parts = parts[2:]
            course_name = ' '.join(course_parts)
            # Clean up the name
            course_name = course_name.replace('.csv', '')
            return course_name
        return None
    
    def get_text_content(self, text_id: str, content_type: str, display_name: str) -> Optional[str]:
        """Get text content from extracted_text folder based on text_id, content_type, and display_name"""
        try:
            # Determine the folder based on content_type
            folder_map = {
                'docx': 'docx',
                'pdf': 'pdf', 
                'pptx': 'pptx',
                'txt': 'txt',
                'zip': 'zip'
            }
            
            folder = folder_map.get(content_type.lower(), 'txt')
            text_dir = self.extracted_text_dir / folder
            
            # Look for the file with display_name + "summary" at the end
            summary_filename = f"{display_name}.summary.txt"
            
            # Find matching files
            for file_path in text_dir.glob("*.txt"):
                if file_path.name.endswith(summary_filename):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            return content
            
            # If no summary found, try without summary suffix
            for file_path in text_dir.glob("*.txt"):
                if display_name in file_path.name and not file_path.name.endswith('.summary.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            return content
                            
        except Exception as e:
            logger.warning(f"Error reading text content for {text_id}: {e}")
        
        return None
    
    def process_files_csv(self, csv_file_path: Path) -> List[Dict]:
        """Process a files CSV and extract text content"""
        logger.info(f"Processing files CSV: {csv_file_path}")
        
        course_id = self.extract_course_id_from_filename(csv_file_path.name)
        course_name = self.extract_course_name_from_filename(csv_file_path.name)
        
        if not course_id:
            logger.warning(f"Could not extract course ID from {csv_file_path.name}")
            return []
        
        try:
            df = pd.read_csv(csv_file_path)
            processed_rows = []
            
            for _, row in df.iterrows():
                # Create course content entry
                text_content = None
                if 'text_id' in row and pd.notna(row['text_id']):
                    text_content = self.get_text_content(
                        str(row['text_id']),
                        row.get('content_type', 'txt'),
                        row.get('display_name', '')
                    )
                
                if text_content:
                    course_content_entry = {
                        'id': self.text_id_counter,
                        'file_name': row.get('display_name', ''),
                        'full_text': text_content
                    }
                    self.course_content_data.append(course_content_entry)
                    
                    # Create course content summary entry
                    summary_entry = {
                        'canvas_id': row.get('id', ''),
                        'course_name': course_name,
                        'type': 'file',
                        'title': row.get('display_name', ''),
                        'date': row.get('created_at', ''),
                        'link': row.get('url', ''),
                        'is_completed': '',
                        'grade': '',
                        'summary': '',
                        'text_id': self.text_id_counter
                    }
                    processed_rows.append(summary_entry)
                    self.text_id_counter += 1
                else:
                    # Create entry without text content
                    summary_entry = {
                        'canvas_id': row.get('id', ''),
                        'course_name': course_name,
                        'type': 'file',
                        'title': row.get('display_name', ''),
                        'date': row.get('created_at', ''),
                        'link': row.get('url', ''),
                        'is_completed': '',
                        'grade': '',
                        'summary': '',
                        'text_id': 'N/A'
                    }
                    processed_rows.append(summary_entry)
            
            return processed_rows
            
        except Exception as e:
            logger.error(f"Error processing {csv_file_path}: {e}")
            return []
    
    def process_assignments_csv(self, csv_file_path: Path) -> List[Dict]:
        """Process an assignments CSV"""
        logger.info(f"Processing assignments CSV: {csv_file_path}")
        
        course_id = self.extract_course_id_from_filename(csv_file_path.name)
        course_name = self.extract_course_name_from_filename(csv_file_path.name)
        
        if not course_id:
            logger.warning(f"Could not extract course ID from {csv_file_path.name}")
            return []
        
        try:
            df = pd.read_csv(csv_file_path)
            processed_rows = []
            
            for _, row in df.iterrows():
                summary_entry = {
                    'canvas_id': row.get('id', ''),
                    'course_name': course_name,
                    'type': 'assignment',
                    'title': row.get('name', ''),
                    'date': row.get('due_at', ''),
                    'link': row.get('html_url', ''),
                    'is_completed': '',
                    'grade': row.get('points_possible', ''),
                    'summary': '',
                    'text_id': 'N/A'
                }
                processed_rows.append(summary_entry)
            
            return processed_rows
            
        except Exception as e:
            logger.error(f"Error processing {csv_file_path}: {e}")
            return []
    
    def process_modules_csv(self, csv_file_path: Path) -> List[Dict]:
        """Process a modules CSV"""
        logger.info(f"Processing modules CSV: {csv_file_path}")
        
        course_id = self.extract_course_id_from_filename(csv_file_path.name)
        course_name = self.extract_course_name_from_filename(csv_file_path.name)
        
        if not course_id:
            logger.warning(f"Could not extract course ID from {csv_file_path.name}")
            return []
        
        try:
            df = pd.read_csv(csv_file_path)
            processed_rows = []
            
            for _, row in df.iterrows():
                summary_entry = {
                    'canvas_id': row.get('id', ''),
                    'course_name': course_name,
                    'type': 'module',
                    'title': row.get('name', ''),
                    'date': row.get('created_at', ''),
                    'link': '',
                    'is_completed': '',
                    'grade': '',
                    'summary': '',
                    'text_id': 'N/A'
                }
                processed_rows.append(summary_entry)
            
            return processed_rows
            
        except Exception as e:
            logger.error(f"Error processing {csv_file_path}: {e}")
            return []
    
    def process_pages_csv(self, csv_file_path: Path) -> List[Dict]:
        """Process a pages CSV"""
        logger.info(f"Processing pages CSV: {csv_file_path}")
        
        course_id = self.extract_course_id_from_filename(csv_file_path.name)
        course_name = self.extract_course_name_from_filename(csv_file_path.name)
        
        if not course_id:
            logger.warning(f"Could not extract course ID from {csv_file_path.name}")
            return []
        
        try:
            df = pd.read_csv(csv_file_path)
            processed_rows = []
            
            for _, row in df.iterrows():
                summary_entry = {
                    'canvas_id': row.get('id', ''),
                    'course_name': course_name,
                    'type': 'page',
                    'title': row.get('title', ''),
                    'date': row.get('created_at', ''),
                    'link': row.get('url', ''),
                    'is_completed': '',
                    'grade': '',
                    'summary': '',
                    'text_id': 'N/A'
                }
                processed_rows.append(summary_entry)
            
            return processed_rows
            
        except Exception as e:
            logger.error(f"Error processing {csv_file_path}: {e}")
            return []
    
    def process_module_items_csv(self, csv_file_path: Path) -> List[Dict]:
        """Process a module_items CSV"""
        logger.info(f"Processing module_items CSV: {csv_file_path}")
        
        course_id = self.extract_course_id_from_filename(csv_file_path.name)
        course_name = self.extract_course_name_from_filename(csv_file_path.name)
        
        if not course_id:
            logger.warning(f"Could not extract course ID from {csv_file_path.name}")
            return []
        
        try:
            df = pd.read_csv(csv_file_path)
            processed_rows = []
            
            for _, row in df.iterrows():
                summary_entry = {
                    'canvas_id': row.get('id', ''),
                    'course_name': course_name,
                    'type': 'module_item',
                    'title': row.get('title', ''),
                    'date': row.get('created_at', ''),
                    'link': row.get('url', ''),
                    'is_completed': '',
                    'grade': '',
                    'summary': '',
                    'text_id': 'N/A'
                }
                processed_rows.append(summary_entry)
            
            return processed_rows
            
        except Exception as e:
            logger.error(f"Error processing {csv_file_path}: {e}")
            return []
    
    def process_quizzes_csv(self, csv_file_path: Path) -> List[Dict]:
        """Process a quizzes CSV"""
        logger.info(f"Processing quizzes CSV: {csv_file_path}")
        
        course_id = self.extract_course_id_from_filename(csv_file_path.name)
        course_name = self.extract_course_name_from_filename(csv_file_path.name)
        
        if not course_id:
            logger.warning(f"Could not extract course ID from {csv_file_path.name}")
            return []
        
        try:
            df = pd.read_csv(csv_file_path)
            processed_rows = []
            
            for _, row in df.iterrows():
                summary_entry = {
                    'canvas_id': row.get('id', ''),
                    'course_name': course_name,
                    'type': 'quiz',
                    'title': row.get('title', ''),
                    'date': row.get('due_at', ''),
                    'link': row.get('html_url', ''),
                    'is_completed': '',
                    'grade': row.get('points_possible', ''),
                    'summary': '',
                    'text_id': 'N/A'
                }
                processed_rows.append(summary_entry)
            
            return processed_rows
            
        except Exception as e:
            logger.error(f"Error processing {csv_file_path}: {e}")
            return []
    
    def create_course_content_summary(self):
        """Create course_content_summary.csv by processing all source CSV files"""
        logger.info("Creating course_content_summary.csv")
        
        # First, try to process source CSV files if they exist
        csv_files = list(self.data_dir.glob("*.csv"))
        source_files_found = False
        
        for csv_file in csv_files:
            filename = csv_file.name.lower()
            
            if filename.startswith('files_'):
                self.course_content_summary_data.extend(self.process_files_csv(csv_file))
                source_files_found = True
            elif filename.startswith('assignments_'):
                self.course_content_summary_data.extend(self.process_assignments_csv(csv_file))
                source_files_found = True
            elif filename.startswith('modules_'):
                self.course_content_summary_data.extend(self.process_modules_csv(csv_file))
                source_files_found = True
            elif filename.startswith('module_items_'):
                self.course_content_summary_data.extend(self.process_module_items_csv(csv_file))
                source_files_found = True
            elif filename.startswith('pages_'):
                self.course_content_summary_data.extend(self.process_pages_csv(csv_file))
                source_files_found = True
            elif filename.startswith('quizzes_'):
                self.course_content_summary_data.extend(self.process_quizzes_csv(csv_file))
                source_files_found = True
        
        # If no source files found, copy existing course_content_summary.csv
        if not source_files_found:
            logger.info("No source CSV files found, copying existing course_content_summary.csv")
            existing_summary = self.data_dir / "course_content_summary.csv"
            if existing_summary.exists():
                df_existing = pd.read_csv(existing_summary)
                self.course_content_summary_data = df_existing.to_dict('records')
                logger.info(f"Copied existing course_content_summary.csv with {len(self.course_content_summary_data)} rows")
            else:
                logger.warning("No existing course_content_summary.csv found")
        
        # Write course_content_summary.csv
        if self.course_content_summary_data:
            df_summary = pd.DataFrame(self.course_content_summary_data)
            output_file = self.output_dir / "course_content_summary.csv"
            df_summary.to_csv(output_file, index=False)
            logger.info(f"Created {output_file} with {len(self.course_content_summary_data)} rows")
    
    def create_course_content(self):
        """Create course_content.csv with extracted text content"""
        logger.info("Creating course_content.csv")
        
        # If no course content data was created from source files, copy existing
        if not self.course_content_data:
            logger.info("No course content data from source files, copying existing course_content.csv")
            existing_content = self.data_dir / "course_content.csv"
            if existing_content.exists():
                df_existing = pd.read_csv(existing_content)
                self.course_content_data = df_existing.to_dict('records')
                logger.info(f"Copied existing course_content.csv with {len(self.course_content_data)} rows")
            else:
                logger.warning("No existing course_content.csv found")
        
        if self.course_content_data:
            df_content = pd.DataFrame(self.course_content_data)
            output_file = self.output_dir / "course_content.csv"
            df_content.to_csv(output_file, index=False)
            logger.info(f"Created {output_file} with {len(self.course_content_data)} rows")
        else:
            logger.warning("No course content data found")
    
    def create_courses_csv(self):
        """Create courses.csv from existing courses.csv"""
        logger.info("Creating courses.csv")
        
        try:
            # Copy existing courses.csv
            existing_courses = self.data_dir / "courses.csv"
            if existing_courses.exists():
                df_courses = pd.read_csv(existing_courses)
                output_file = self.output_dir / "courses.csv"
                df_courses.to_csv(output_file, index=False)
                logger.info(f"Created {output_file} with {len(df_courses)} rows")
            else:
                logger.warning("No existing courses.csv found")
        except Exception as e:
            logger.error(f"Error creating courses.csv: {e}")
    
    def create_users_csv(self):
        """Create users.csv from existing canvas_user_self.csv"""
        logger.info("Creating users.csv")
        
        try:
            # Copy and rename existing canvas_user_self.csv
            existing_users = self.data_dir / "canvas_user_self.csv"
            if existing_users.exists():
                df_users = pd.read_csv(existing_users)
                output_file = self.output_dir / "users.csv"
                df_users.to_csv(output_file, index=False)
                logger.info(f"Created {output_file} with {len(df_users)} rows")
            else:
                logger.warning("No existing canvas_user_self.csv found")
        except Exception as e:
            logger.error(f"Error creating users.csv: {e}")
    
    def create_grades_csv(self):
        """Create grades.csv from existing user_grades_self.csv"""
        logger.info("Creating grades.csv")
        
        try:
            # Copy and rename existing user_grades_self.csv
            existing_grades = self.data_dir / "user_grades_self.csv"
            if existing_grades.exists():
                df_grades = pd.read_csv(existing_grades)
                output_file = self.output_dir / "grades.csv"
                df_grades.to_csv(output_file, index=False)
                logger.info(f"Created {output_file} with {len(df_grades)} rows")
            else:
                logger.warning("No existing user_grades_self.csv found")
        except Exception as e:
            logger.error(f"Error creating grades.csv: {e}")
    
    def create_sample_source_files(self):
        """Create sample source CSV files for testing purposes"""
        logger.info("Creating sample source CSV files")
        
        # Create sample assignments CSV
        sample_assignments = [
            {
                'id': '10500000016380828',
                'name': 'Sample Assignment 1',
                'due_at': '2024-10-02T18:30:00Z',
                'points_possible': 100.0,
                'html_url': 'https://canvas.instructure.com/courses/10500000002349828/assignments/1050~16380828'
            },
            {
                'id': '10500000016380815',
                'name': 'Sample Assignment 2',
                'due_at': '2024-11-06T19:30:00Z',
                'points_possible': 150.0,
                'html_url': 'https://canvas.instructure.com/courses/10500000002349828/assignments/1050~16380815'
            }
        ]
        
        assignments_file = self.data_dir / "assignments_10500000002349828_sample_course.csv"
        df_assignments = pd.DataFrame(sample_assignments)
        df_assignments.to_csv(assignments_file, index=False)
        logger.info(f"Created sample assignments file: {assignments_file}")
        
        # Create sample files CSV
        sample_files = [
            {
                'id': '10500000017020442',
                'display_name': 'Sample File 1.pdf',
                'content_type': 'application/pdf',
                'created_at': '2024-09-01T10:00:00Z',
                'url': 'https://canvas.instructure.com/courses/10500000002349828/files/10500000017020442',
                'text_id': 'sample_file_1'
            },
            {
                'id': '10500000017020443',
                'display_name': 'Sample File 2.docx',
                'content_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'created_at': '2024-09-02T10:00:00Z',
                'url': 'https://canvas.instructure.com/courses/10500000002349828/files/10500000017020443',
                'text_id': 'sample_file_2'
            }
        ]
        
        files_file = self.data_dir / "files_10500000002349828_sample_course.csv"
        df_files = pd.DataFrame(sample_files)
        df_files.to_csv(files_file, index=False)
        logger.info(f"Created sample files file: {files_file}")
        
        logger.info("Sample source files created successfully")
    
    def format_all_csvs(self):
        """Main method to format all CSV files"""
        logger.info("Starting CSV formatting process")
        
        # Create all 5 core CSV files
        self.create_course_content_summary()
        self.create_course_content()
        self.create_courses_csv()
        self.create_users_csv()
        self.create_grades_csv()
        
        logger.info("CSV formatting process completed")
        
        # Print summary
        print("\n" + "="*50)
        print("CSV FORMATTING SUMMARY")
        print("="*50)
        print(f"Output directory: {self.output_dir}")
        print(f"Course content summary rows: {len(self.course_content_summary_data)}")
        print(f"Course content rows: {len(self.course_content_data)}")
        print("\nGenerated files:")
        for file in self.output_dir.glob("*.csv"):
            print(f"  - {file.name}")

def main():
    """Main function to run the CSV formatter"""
    import sys
    
    # Check if user wants to create sample files
    if len(sys.argv) > 1 and sys.argv[1] == "--create-samples":
        formatter = CSVFormatter()
        formatter.create_sample_source_files()
        return
    
    formatter = CSVFormatter()
    formatter.format_all_csvs()

if __name__ == "__main__":
    main()
