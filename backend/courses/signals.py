import os
import subprocess
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Lesson


@receiver(post_save, sender=Lesson)
def apply_video_faststart(sender, instance, created, **kwargs):
    """
    Automatically moves MP4 metadata to the front of the file using ffmpeg.
    Fixes the 'NS_ERROR_DOM_MEDIA_RANGE_ERR' in browsers.
    """
    if instance.video_file and os.path.exists(instance.video_file.path):
        input_path = instance.video_file.path

        # Avoid infinite loops and redundant processing
        if input_path.endswith('_qt.mp4'):
            return

        output_path = input_path.replace(".mp4", "_qt.mp4")

        try:
            # ffmpeg command: copy codecs (no re-encoding), move moov atom to front
            command = [
                'ffmpeg', '-y', '-i', input_path,
                '-c', 'copy', '-map', '0',
                '-movflags', '+faststart',
                output_path
            ]

            # Execute ffmpeg inside the container
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                # Remove original unoptimized file
                if os.path.exists(input_path):
                    os.remove(input_path)

                # Update model without triggering signals again
                new_relative_name = os.path.join('lessons/videos/', os.path.basename(output_path))
                Lesson.objects.filter(id=instance.id).update(video_file=new_relative_name)

        except Exception as e:
            print(f"Faststart Error: {e}")