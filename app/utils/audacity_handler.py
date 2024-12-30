import os
import uuid
import subprocess
import logging
import re

class AudioProcessor:
    def __init__(self):
        self.ffmpeg_path = 'ffmpeg'
        self.logger = logging.getLogger(__name__)

    def convert_to_wav(self, input_file):
        """
        Convert input audio file to WAV format
        
        Args:
            input_file (str): Path to input audio file
        
        Returns:
            str: Path to converted WAV file
        """
        try:
            # Generate unique identifier for output
            unique_id = str(uuid.uuid4())[:8]
            print(f"==>> unique_id: {unique_id}")
            
            # Prepare output directories
            input_dir = os.path.dirname(input_file)
            print(f"==>> input_dir: {input_dir}")
            output_dir = os.path.join(input_dir, 'output')
            print(f"==>> output_dir: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename
            output_filename = f'converted_{unique_id}.wav'
            print(f"==>> output_filename: {output_filename}")
            output_path = os.path.join(output_dir, output_filename)
            
            # FFmpeg conversion command
            convert_command = [
                self.ffmpeg_path,
                '-i', input_file,
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '22050',  # Sample rate
                '-ac', '1',  # Mono channel
                output_path
            ]
            
            # Execute conversion
            process = subprocess.run(
                convert_command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                check=True
            )
            
            # Verify file creation
            if not os.path.exists(output_path):
                raise Exception("WAV conversion failed: Output file not created")
            
            self.logger.info(f"Successfully converted to WAV: {output_path}")
            return output_path
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg conversion error: {e.stderr}")
            raise Exception(f"Audio conversion failed: {e.stderr}")
        except Exception as e:
            self.logger.error(f"Conversion error: {str(e)}")
            raise

    def detect_silence(self, wav_file):
        """
        Detect silence points in the audio file
        
        Args:
            wav_file (str): Path to WAV file
        
        Returns:
            str: Silence detection output
        """
        try:
            # Silence detection command
            silence_command = [
                self.ffmpeg_path,
                '-i', wav_file,
                '-af', 'silencedetect=noise=-37dB:d=0.5',
                '-f', 'null',
                '-'
            ]
            
            # Execute silence detection
            process = subprocess.run(
                silence_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # Return stderr (where silence info is logged)
            return process.stderr
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Silence detection error: {e.stderr}")
            raise Exception(f"Silence detection failed: {e.stderr}")

    def parse_silence_points(self, silence_output):
        """
        Parse silence detection output
        
        Args:
            silence_output (str): Raw silence detection output
        
        Returns:
            List[dict]: Detected silence points
        """
        silence_points = []
        
        # Regex patterns for silence start and end
        start_pattern = r'silence_start: (\d+\.\d+)'
        end_pattern = r'silence_end: (\d+\.\d+)'
        
        start_matches = re.findall(start_pattern, silence_output)
        end_matches = re.findall(end_pattern, silence_output)
        
        # Pair silence points
        for start, end in zip(start_matches, end_matches):
            silence_points.append({
                'start': float(start),
                'end': float(end)
            })
        
        return silence_points

    def split_audio(self, wav_file, silence_points=None):
        """
        Split audio file into segments
        
        Args:
            wav_file (str): Path to input WAV file
            silence_points (List[dict], optional): Silence points to use for splitting
            
        Returns:
            List[str]: Paths to generated segment files
        """
        try:
            # Get base directory of input WAV file
            base_output_dir = os.path.dirname(wav_file)
            
            # Find all existing folders that start with 'segments_'
            existing_folders = [f for f in os.listdir(base_output_dir) if f.startswith('segments_')]
            
            # Extract numbers from existing folder names like 'segments_01', 'segments_02', etc.
            existing_numbers = []
            for folder in existing_folders:
                match = re.match(r'(\d+)_segments', folder)
                if match:
                    existing_numbers.append(int(match.group(1)))
            
            # Determine the next folder number based on the highest existing number + 1
            next_number = max(existing_numbers, default=0) + 1
            
            # Format the folder name with leading zeros (e.g., 01, 02, ...)
            output_dir = os.path.join(base_output_dir, f'{str(next_number).zfill(2)}_segments_{str(uuid.uuid4())[:8]}')
            os.makedirs(output_dir, exist_ok=True)
            
            # If no silence points, use default segmentation
            if not silence_points:
                # Fallback to fixed-length segments
                segment_command = [
                    self.ffmpeg_path,
                    '-i', wav_file,
                    '-f', 'segment',
                    '-segment_time', '10',  # 10-second segments
                    '-c', 'copy',
                    os.path.join(output_dir, 'segment_%03d.wav')
                ]
                subprocess.run(segment_command, check=True)
            else:
                # Split based on silence points
                segments = []
                for i, point in enumerate(silence_points):
                    output_segment = os.path.join(
                        output_dir, 
                        f'segment_{i+1:03d}.wav'  # Sequential naming
                    )
                    
                    # Extract segment around silence point
                    segment_command = [
                        self.ffmpeg_path,
                        '-i', wav_file,
                        '-ss', str(max(0, point['start'] - 1)),
                        '-to', str(point['end'] + 1),
                        '-c', 'copy',
                        output_segment
                    ]
                    subprocess.run(segment_command, check=True)
                    
                    if os.path.exists(output_segment):
                        segments.append(output_segment)
            
            # Return all generated segment files
            return [
                f for f in os.listdir(output_dir) 
                if f.endswith('.wav')
            ]
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Audio splitting error: {e}")
            raise Exception(f"Failed to split audio: {e}")



    def process_audio(self, input_file):
        """
        Comprehensive audio processing workflow
        
        Args:
            input_file (str): Path to input audio file
        
        Returns:
            List[str]: Paths to generated segment files
        """
        try:
            # Convert to WAV
            wav_file = self.convert_to_wav(input_file)
            
            # Detect silence
            silence_output = self.detect_silence(wav_file)
            
            # Parse silence points
            silence_points = self.parse_silence_points(silence_output)
            
            # Split audio
            segments = self.split_audio(wav_file, silence_points)
            
            self.logger.info(f"Generated {len(segments)} audio segments")
            return segments
        
        except Exception as e:
            self.logger.error(f"Audio processing failed: {str(e)}")
            raise


















# # app/utils/audacity_handler.py
# import os
# import uuid
# import subprocess
# import logging
# import re

# class AudioProcessor:
#     def __init__(self):
#         self.ffmpeg_path = 'ffmpeg'
#         self.logger = logging.getLogger(__name__)

#     def convert_to_wav(self, input_file):
#         """
#         Convert input audio file to WAV format
        
#         Args:
#             input_file (str): Path to input audio file
        
#         Returns:
#             str: Path to converted WAV file
#         """
#         try:
#             # Generate unique identifier for output
#             unique_id = str(uuid.uuid4())[:8]
#             print(f"==>> unique_id: {unique_id}")
            
#             # Prepare output directories
#             input_dir = os.path.dirname(input_file)
#             print(f"==>> input_dir: {input_dir}")
#             output_dir = os.path.join(input_dir, 'output')
#             print(f"==>> output_dir: {output_dir}")
#             os.makedirs(output_dir, exist_ok=True)
            
#             # Generate output filename
#             output_filename = f'converted_{unique_id}.wav'
#             print(f"==>> output_filename: {output_filename}")
#             output_path = os.path.join(output_dir, output_filename)
            
#             # FFmpeg conversion command
#             convert_command = [
#                 self.ffmpeg_path,
#                 '-i', input_file,
#                 '-acodec', 'pcm_s16le',  # 16-bit PCM
#                 '-ar', '22050',  # Sample rate
#                 '-ac', '1',  # Mono channel
#                 output_path
#             ]
            
#             # Execute conversion
#             process = subprocess.run(
#                 convert_command, 
#                 stdout=subprocess.PIPE, 
#                 stderr=subprocess.PIPE, 
#                 text=True,
#                 check=True
#             )
            
#             # Verify file creation
#             if not os.path.exists(output_path):
#                 raise Exception("WAV conversion failed: Output file not created")
            
#             self.logger.info(f"Successfully converted to WAV: {output_path}")
#             return output_path
        
#         except subprocess.CalledProcessError as e:
#             self.logger.error(f"FFmpeg conversion error: {e.stderr}")
#             raise Exception(f"Audio conversion failed: {e.stderr}")
#         except Exception as e:
#             self.logger.error(f"Conversion error: {str(e)}")
#             raise

#     def detect_silence(self, wav_file):
#         """
#         Detect silence points in the audio file
        
#         Args:
#             wav_file (str): Path to WAV file
        
#         Returns:
#             str: Silence detection output
#         """
#         try:
#             # Silence detection command
#             silence_command = [
#                 self.ffmpeg_path,
#                 '-i', wav_file,
#                 '-af', 'silencedetect=noise=-37dB:d=0.5',
#                 '-f', 'null',
#                 '-'
#             ]
            
#             # Execute silence detection
#             process = subprocess.run(
#                 silence_command,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True,
#                 check=True
#             )
            
#             # Return stderr (where silence info is logged)
#             return process.stderr
        
#         except subprocess.CalledProcessError as e:
#             self.logger.error(f"Silence detection error: {e.stderr}")
#             raise Exception(f"Silence detection failed: {e.stderr}")

#     def parse_silence_points(self, silence_output):
#         """
#         Parse silence detection output
        
#         Args:
#             silence_output (str): Raw silence detection output
        
#         Returns:
#             List[dict]: Detected silence points
#         """
#         silence_points = []
        
#         # Regex patterns for silence start and end
#         start_pattern = r'silence_start: (\d+\.\d+)'
#         end_pattern = r'silence_end: (\d+\.\d+)'
        
#         start_matches = re.findall(start_pattern, silence_output)
#         end_matches = re.findall(end_pattern, silence_output)
        
#         # Pair silence points
#         for start, end in zip(start_matches, end_matches):
#             silence_points.append({
#                 'start': float(start),
#                 'end': float(end)
#             })
        
#         return silence_points

#     def split_audio(self, wav_file, silence_points=None):
#         """
#         Split audio file into segments
        
#         Args:
#             wav_file (str): Path to input WAV file
#             silence_points (List[dict], optional): Silence points to use for splitting
        
#         Returns:
#             List[str]: Paths to generated segment files
#         """
#         try:
#             # Create unique output directory
#             unique_id = str(uuid.uuid4())[:8]
#             output_dir = os.path.join(
#                 os.path.dirname(wav_file), 
#                 f'segments_{unique_id}'
#             )
#             os.makedirs(output_dir, exist_ok=True)
            
#             # If no silence points, use default segmentation
#             if not silence_points:
#                 # Fallback to fixed-length segments
#                 segment_command = [
#                     self.ffmpeg_path,
#                     '-i', wav_file,
#                     '-f', 'segment',
#                     '-segment_time', '10',  # 10-second segments
#                     '-c', 'copy',
#                     os.path.join(output_dir, 'segment_%03d.wav')
#                 ]
                
#                 subprocess.run(segment_command, check=True)
#             else:
#                 # Split based on silence points
#                 segments = []
#                 for i, point in enumerate(silence_points):
#                     output_segment = os.path.join(
#                         output_dir, 
#                         f'segment_{i:03d}.wav'
#                     )
                    
#                     # Extract segment around silence point
#                     segment_command = [
#                         self.ffmpeg_path,
#                         '-i', wav_file,
#                         '-ss', str(max(0, point['start'] - 1)),
#                         '-to', str(point['end'] + 1),
#                         '-c', 'copy',
#                         output_segment
#                     ]
                    
#                     subprocess.run(segment_command, check=True)
                    
#                     if os.path.exists(output_segment):
#                         segments.append(output_segment)
            
#             # Return all generated segment files
#             return [
#                 f for f in os.listdir(output_dir) 
#                 if f.endswith('.wav')
#             ]
        
#         except subprocess.CalledProcessError as e:
#             self.logger.error(f"Audio splitting error: {e}")
#             raise Exception(f"Failed to split audio: {e}")

#     def process_audio(self, input_file):
#         """
#         Comprehensive audio processing workflow
        
#         Args:
#             input_file (str): Path to input audio file
        
#         Returns:
#             List[str]: Paths to generated segment files
#         """
#         try:
#             # Convert to WAV
#             wav_file = self.convert_to_wav(input_file)
            
#             # Detect silence
#             silence_output = self.detect_silence(wav_file)
            
#             # Parse silence points
#             silence_points = self.parse_silence_points(silence_output)
            
#             # Split audio
#             segments = self.split_audio(wav_file, silence_points)
            
#             self.logger.info(f"Generated {len(segments)} audio segments")
#             return segments
        
#         except Exception as e:
#             self.logger.error(f"Audio processing failed: {str(e)}")
#             raise