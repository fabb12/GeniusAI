import logging
import sys

class StreamToLogger(object):
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

def setup_logging():
    logging.basicConfig(
        filename='../console_log.txt',
        level=logging.DEBUG,
        format='[%(asctime)s - %(levelname)s] - %(message)s'
    )

    stdout_logger = logging.getLogger('STDOUT')
    stdout_logger.setLevel(logging.INFO)
    stderr_logger = logging.getLogger('STDERR')
    stderr_logger.setLevel(logging.ERROR)

    sys.stdout = StreamToLogger(stdout_logger, logging.INFO)
    sys.stderr = StreamToLogger(stderr_logger, logging.ERROR)

if __name__ == "__main__":
    setup_logging()
    print("This is a test message for stdout")
    print("This is an error message for stderr", file=sys.stderr)
