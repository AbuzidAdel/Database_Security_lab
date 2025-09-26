#!/usr/bin/env python3
"""
Content Migration Script for Database Security Lab
Parses existing HTML files and imports them into the new system
"""

import os
import re
import json
import boto3
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentMigrator:
    def __init__(self, html_dir=".", aws_region="us-east-1"):
        self.html_dir = Path(html_dir)
        self.aws_region = aws_region
        self.dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        self.content_table = self.dynamodb.Table(os.getenv('CONTENT_TABLE', 'database-security-lab-content'))
        
        # Content structure
        self.exercises = {}
        self.steps = {}
        self.references = {}
        
    def parse_html_files(self):
        """Parse all HTML files and extract content structure"""
        logger.info("Starting HTML file parsing...")
        
        # Find all HTML files
        html_files = list(self.html_dir.glob("*.html"))
        logger.info(f"Found {len(html_files)} HTML files")
        
        for html_file in html_files:
            self.parse_single_file(html_file)
        
        logger.info(f"Parsed {len(self.exercises)} exercises, {len(self.steps)} steps, {len(self.references)} references")
    
    def parse_single_file(self, html_file):
        """Parse a single HTML file"""
        filename = html_file.name
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Determine file type based on filename pattern
            if re.match(r'^e\d+\.html$', filename):
                # Main exercise file (e1.html, e2.html, etc.)
                self.parse_exercise_index(filename, soup)
            elif re.match(r'^e\d+-\d+\.html$', filename):
                # Sub-exercise file (e1-1.html, e1-2.html, etc.)
                self.parse_sub_exercise(filename, soup)
            elif re.match(r'^e\d+-\d+-A\d+\.html$', filename):
                # Step content file (e1-1-A0.html, e1-1-A1.html, etc.)
                self.parse_step_content(filename, soup)
            elif filename.endswith('-REFS.html'):
                # References file
                self.parse_references(filename, soup)
            elif filename.endswith('-frame.html'):
                # Frame files - skip these as they're just navigation
                pass
            else:
                logger.debug(f"Skipping file with unknown pattern: {filename}")
                
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
    
    def parse_exercise_index(self, filename, soup):
        """Parse main exercise index file"""
        exercise_num = re.search(r'e(\d+)\.html', filename).group(1)
        exercise_id = f"exercise_{exercise_num}"
        
        # Extract title and content
        header = soup.find(class_='header')
        title = header.get_text().strip() if header else f"Exercise {exercise_num}"
        
        # Extract sub-exercises links
        links = soup.find_all('a', class_='toplink')
        content_parts = [f"<h2>{title}</h2>"]
        
        if links:
            content_parts.append("<p>This exercise contains the following sections:</p>")
            content_parts.append("<ul>")
            for link in links:
                link_text = link.get_text().strip()
                content_parts.append(f"<li>{link_text}</li>")
            content_parts.append("</ul>")
        
        self.exercises[exercise_id] = {
            'id': exercise_id,
            'title': title,
            'content': '\n'.join(content_parts),
            'content_type': 'exercise',
            'order': int(exercise_num),
            'is_hidden': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Parsed exercise: {title}")
    
    def parse_sub_exercise(self, filename, soup):
        """Parse sub-exercise file"""
        match = re.search(r'e(\d+)-(\d+)\.html', filename)
        exercise_num = match.group(1)
        sub_num = match.group(2)
        
        exercise_id = f"exercise_{exercise_num}_{sub_num}"
        parent_id = f"exercise_{exercise_num}"
        
        # Extract title
        header = soup.find(class_='header')
        if header:
            title_text = header.get_text().strip()
            # Clean up the title
            title = re.sub(r'^Recipe \d+\.\d+\s*', '', title_text)
            title = re.sub(r'\n+', ' ', title).strip()
        else:
            title = f"Exercise {exercise_num}.{sub_num}"
        
        # Extract steps
        steps_links = soup.find_all('a', class_='toplink')
        content_parts = [f"<h3>{title}</h3>"]
        
        if steps_links:
            content_parts.append("<p>This section includes the following steps:</p>")
            content_parts.append("<ol>")
            for i, link in enumerate(steps_links):
                if 'REFS.html' not in link.get('href', ''):
                    link_text = link.get_text().strip()
                    content_parts.append(f"<li>{link_text}</li>")
            content_parts.append("</ol>")
        
        self.exercises[exercise_id] = {
            'id': exercise_id,
            'title': title,
            'content': '\n'.join(content_parts),
            'content_type': 'exercise',
            'parent_id': parent_id,
            'order': int(sub_num),
            'is_hidden': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Parsed sub-exercise: {title}")
    
    def parse_step_content(self, filename, soup):
        """Parse step content file"""
        # Note: The actual step content files don't exist in the current structure
        # This is a placeholder for when they do exist
        match = re.search(r'e(\d+)-(\d+)-A(\d+)\.html', filename)
        if not match:
            return
            
        exercise_num = match.group(1)
        sub_num = match.group(2)
        step_num = match.group(3)
        
        step_id = f"step_{exercise_num}_{sub_num}_{step_num}"
        parent_id = f"exercise_{exercise_num}_{sub_num}"
        
        # Extract content
        body_content = soup.find('body')
        if body_content:
            # Clean up the content
            content = str(body_content)
            content = re.sub(r'<body[^>]*>', '', content)
            content = re.sub(r'</body>', '', content)
            content = content.strip()
        else:
            content = f"<p>Step {step_num} content</p>"
        
        title = f"Step {step_num}"
        
        self.steps[step_id] = {
            'id': step_id,
            'title': title,
            'content': content,
            'content_type': 'step',
            'parent_id': parent_id,
            'order': int(step_num),
            'is_hidden': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Parsed step: {title}")
    
    def parse_references(self, filename, soup):
        """Parse references file"""
        match = re.search(r'e(\d+)-(\d+)-REFS\.html', filename)
        if not match:
            return
            
        exercise_num = match.group(1)
        sub_num = match.group(2)
        
        ref_id = f"references_{exercise_num}_{sub_num}"
        parent_id = f"exercise_{exercise_num}_{sub_num}"
        
        # Extract references content
        body_content = soup.find('body')
        if body_content:
            content = str(body_content)
            content = re.sub(r'<body[^>]*>', '', content)
            content = re.sub(r'</body>', '', content)
            content = content.strip()
        else:
            content = "<p>References</p>"
        
        title = "References"
        
        self.references[ref_id] = {
            'id': ref_id,
            'title': title,
            'content': content,
            'content_type': 'reference',
            'parent_id': parent_id,
            'order': 999,  # References come last
            'is_hidden': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Parsed references for exercise {exercise_num}-{sub_num}")
    
    def create_placeholder_steps(self):
        """Create placeholder steps for exercises that don't have actual step content"""
        logger.info("Creating placeholder steps...")
        
        for exercise_id, exercise in self.exercises.items():
            if exercise.get('parent_id'):  # This is a sub-exercise
                # Create some placeholder steps
                for i in range(1, 6):  # Create 5 placeholder steps
                    step_id = f"step_{exercise_id}_{i}"
                    
                    if step_id not in self.steps:
                        self.steps[step_id] = {
                            'id': step_id,
                            'title': f"Step {i}",
                            'content': f"<p>This is step {i} of {exercise['title']}.</p><p>Content will be added here.</p>",
                            'content_type': 'step',
                            'parent_id': exercise_id,
                            'order': i,
                            'is_hidden': False,
                            'created_at': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat()
                        }
        
        logger.info(f"Created {len(self.steps)} total steps")
    
    def save_to_dynamodb(self):
        """Save all parsed content to DynamoDB"""
        logger.info("Saving content to DynamoDB...")
        
        all_items = []
        all_items.extend(self.exercises.values())
        all_items.extend(self.steps.values())
        all_items.extend(self.references.values())
        
        # Batch write to DynamoDB
        with self.content_table.batch_writer() as batch:
            for item in all_items:
                try:
                    batch.put_item(Item=item)
                    logger.debug(f"Saved: {item['title']}")
                except Exception as e:
                    logger.error(f"Error saving {item['id']}: {e}")
        
        logger.info(f"Saved {len(all_items)} items to DynamoDB")
    
    def export_to_json(self, output_file="migrated_content.json"):
        """Export parsed content to JSON file for backup"""
        all_content = {
            'exercises': self.exercises,
            'steps': self.steps,
            'references': self.references,
            'migration_date': datetime.utcnow().isoformat()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported content to {output_file}")
    
    def migrate(self, save_to_db=True, export_json=True):
        """Run the complete migration process"""
        logger.info("Starting content migration...")
        
        # Parse HTML files
        self.parse_html_files()
        
        # Create placeholder steps
        self.create_placeholder_steps()
        
        # Export to JSON
        if export_json:
            self.export_to_json()
        
        # Save to DynamoDB
        if save_to_db:
            self.save_to_dynamodb()
        
        logger.info("Migration completed successfully!")
        
        # Print summary
        print("\n" + "="*50)
        print("MIGRATION SUMMARY")
        print("="*50)
        print(f"Exercises: {len(self.exercises)}")
        print(f"Steps: {len(self.steps)}")
        print(f"References: {len(self.references)}")
        print(f"Total items: {len(self.exercises) + len(self.steps) + len(self.references)}")
        print("="*50)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate HTML content to Database Security Lab')
    parser.add_argument('--html-dir', default='.', help='Directory containing HTML files')
    parser.add_argument('--aws-region', default='us-east-1', help='AWS region')
    parser.add_argument('--no-db', action='store_true', help='Skip saving to DynamoDB')
    parser.add_argument('--no-json', action='store_true', help='Skip JSON export')
    
    args = parser.parse_args()
    
    migrator = ContentMigrator(args.html_dir, args.aws_region)
    migrator.migrate(
        save_to_db=not args.no_db,
        export_json=not args.no_json
    )

if __name__ == "__main__":
    main()