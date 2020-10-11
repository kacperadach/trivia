from time import sleep
from datetime import datetime
from threading import Lock, Thread

LOCK_TIMEOUT = 5

class TimeoutLock:

    def __init__(self):
        self.lock = Lock()
        self.acquired = None
        t = Thread(target=self._timeout_lock)
        t.start()


    def _timeout_lock(self):
        while True:
            sleep(0.05)
            if self.acquired:
                if (datetime.now() - self.acquired).total_seconds() > LOCK_TIMEOUT:
                    self.acquired = None
                    self.lock.release()

    def acquire(self):
        self.lock.acquire()
        self.acquired = datetime.now()

    def release(self):
        self.acquired = None
        self.lock.release()
