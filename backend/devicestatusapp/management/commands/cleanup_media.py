import os
import time
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Cleans up CCTV photos and videos to prevent VPS storage bloat'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Retention period in days (delete files older than this)')
        parser.add_argument('--max-size', type=int, default=2000, help='Maximum allowed directory size in MB')
        parser.add_argument('--target-size', type=int, default=1500, help='Target directory size in MB after cleaning up capacity')

    def handle(self, *args, **options):
        retention_days = options['days']
        max_size_mb = options.get('max_size', options.get('max-size', 2000))
        target_size_mb = options.get('target_size', options.get('target-size', 1500))
        
        self.stdout.write(self.style.WARNING(
            f"Starting CCTV media cleanup... Policy: Age > {retention_days} days OR Capacity > {max_size_mb} MB"
        ))

        # Check directories
        media_cctv_dir = os.path.join(settings.MEDIA_ROOT, "cctv")
        photos_dir = os.path.join(media_cctv_dir, "photos")
        videos_dir = os.path.join(media_cctv_dir, "videos")

        # Gather all CCTV capture files
        files_metadata = []
        
        for folder_dir in [photos_dir, videos_dir]:
            if not os.path.exists(folder_dir):
                continue
            for f in os.listdir(folder_dir):
                # Ignore system hidden files or legacy _latest marker files
                if f.startswith('.') or "_latest" in f:
                    continue
                filepath = os.path.join(folder_dir, f)
                if os.path.isfile(filepath):
                    try:
                        mtime = os.path.getmtime(filepath)
                        size_bytes = os.path.getsize(filepath)
                        files_metadata.append({
                            'path': filepath,
                            'name': f,
                            'mtime': mtime,
                            'size': size_bytes
                        })
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error accessing {f}: {e}"))

        if not files_metadata:
            self.stdout.write(self.style.SUCCESS("No media files found to clean up."))
            return

        # 1. Age-Based Cleanup
        now_time = time.time()
        retention_seconds = retention_days * 86400
        deleted_age_count = 0
        deleted_age_bytes = 0
        
        remaining_files = []
        for file_info in files_metadata:
            age_seconds = now_time - file_info['mtime']
            if age_seconds > retention_seconds:
                try:
                    os.remove(file_info['path'])
                    deleted_age_count += 1
                    deleted_age_bytes += file_info['size']
                    self.stdout.write(f"Deleted (Age-based): {file_info['name']}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to delete {file_info['name']}: {e}"))
            else:
                remaining_files.append(file_info)

        if deleted_age_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"Age cleanup complete. Deleted {deleted_age_count} files ({round(deleted_age_bytes / (1024*1024), 2)} MB)"
            ))

        # 2. Capacity-Based Cleanup
        # Calculate current total size of remaining files
        total_size_bytes = sum(f['size'] for f in remaining_files)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        self.stdout.write(f"Current CCTV folder size: {round(total_size_mb, 2)} MB")

        if total_size_mb > max_size_mb:
            self.stdout.write(self.style.WARNING(
                f"Folder size exceeds max limit of {max_size_mb} MB. Cleaning up to target {target_size_mb} MB..."
            ))
            
            # Sort remaining files by mtime ascending (oldest first)
            remaining_files.sort(key=lambda x: x['mtime'])
            
            deleted_cap_count = 0
            deleted_cap_bytes = 0
            
            for file_info in remaining_files:
                if total_size_mb <= target_size_mb:
                    break
                try:
                    os.remove(file_info['path'])
                    deleted_cap_count += 1
                    deleted_cap_bytes += file_info['size']
                    total_size_bytes -= file_info['size']
                    total_size_mb = total_size_bytes / (1024 * 1024)
                    self.stdout.write(f"Deleted (Capacity-based/Oldest): {file_info['name']}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to delete {file_info['name']}: {e}"))

            self.stdout.write(self.style.SUCCESS(
                f"Capacity cleanup complete. Deleted {deleted_cap_count} files ({round(deleted_cap_bytes / (1024*1024), 2)} MB). "
                f"New folder size: {round(total_size_mb, 2)} MB"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("Folder size is within limit. No capacity cleanup needed."))
