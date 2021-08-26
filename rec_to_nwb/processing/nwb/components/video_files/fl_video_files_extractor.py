import logging.config
import os

import numpy as np
from rec_to_binaries.read_binaries import readTrodesExtractedDataFile
from rec_to_nwb.processing.tools.beartype.beartype import beartype

path = os.path.dirname(os.path.abspath(__file__))
logging.config.fileConfig(
    fname=os.path.join(str(path), os.pardir, os.pardir,
                       os.pardir, os.pardir, 'logging.conf'),
    disable_existing_loggers=False)
logger = logging.getLogger(__name__)

NANOSECONDS_PER_SECOND = 1E9


class FlVideoFilesExtractor:

    @beartype
    def __init__(self,
                 raw_data_path: str,
                 video_files_metadata: list,
                 convert_timestamps: bool = True,
                 return_timestamps: bool = True):
        self.raw_data_path = raw_data_path
        self.video_files_metadata = video_files_metadata
        self.convert_timestamps = convert_timestamps
        self.return_timestamps = return_timestamps

    def extract_video_files(self):
        """Returns the name, timestamps and device for each video file"""
        video_files = self.video_files_metadata
        extracted_video_files = []
        for video_file in video_files:
            if self.return_timestamps:
                timestamps = self._get_timestamps(video_file)
            else:
                timestamps = np.array([])
            new_fl_video_file = {
                "name": video_file["name"],
                "timestamps": timestamps,
                "device": video_file["camera_id"]
            }
            extracted_video_files.append(new_fl_video_file)
        return extracted_video_files

    def _get_timestamps(self, video_file):
        """Retrieves the video timestamps.

        Timestamps are in units of seconds and will be either relative to the
        start of the recording (if old dataset) or in seconds since 1/1/1970
        if precision time protocol (PTP) is used to synchronize the camera
        frames to Trodes data packets.

        Parameters
        ----------
        video_file : str

        Returns
        -------
        timestamps : ndarray

        """
        try:
            video_timestamps = self._read_video_timestamps_hw_sync(video_file)
            logger.info('Loaded cameraHWSync timestamps for {}'.format(
                video_file['name'][:-4]))
            is_old_dataset = False
        except FileNotFoundError:
            # old dataset
            video_timestamps = self._read_video_timestamps_hw_framecount(
                video_file)
            logger.info(
                'Loaded cameraHWFrameCount for {} (old dataset)'.format(
                    video_file['name'][:-4]))
            is_old_dataset = True
        # the timestamps array from the cam
        if is_old_dataset or (not self.convert_timestamps):
            # for now, FORCE turn off convert_timestamps for old dataset
            return video_timestamps
        return self._convert_timestamps(video_timestamps)

    def _read_video_timestamps_hw_sync(self, video_file):
        """Returns video timestamps in unix time which are synchronized to the
        Trodes data packets.

        videoTimeStamps.cameraHWSync is a file extracted by the python package
        `rec_to_binaries` from the .rec file. It only is extracted when using
        precision time protocol (PTP) to synchronize the camera clock with
        Trodes data packets. The HWTimestamp array in this file are the unix
        timestamps relative to seconds since 1/1/1970.

        Parameters
        ----------
        video_file : str

        Returns
        -------
        unix_timestamps : ndarray

        """
        return readTrodesExtractedDataFile(
            os.path.join(
                self.raw_data_path,
                video_file["name"][:-4] +
                "videoTimeStamps.cameraHWSync")['data']['HWTimestamp'])

    def _read_video_timestamps_hw_framecount(self, video_file):
        """Returns the index of video frames.

        If PTP is not in use, only the videoTimeStamps.cameraHWFrameCount
        file is generated by the `rec_to_binaries` package.

        Parameters
        ----------
        video_file : str

        Returns
        -------
        index : ndarray

        """
        return readTrodesExtractedDataFile(
            os.path.join(
                self.raw_data_path,
                video_file["name"][:-4] +
                "videoTimeStamps.cameraHWFrameCount")['data']['frameCount'])

    def _convert_timestamps(self, timestamps):
        """Converts timestamps from nanoseconds to seconds

        Parameters
        ----------
        timestamps : int

        Returns
        -------
        timestamps : float

        """
        return timestamps / NANOSECONDS_PER_SECOND
