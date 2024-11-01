class Events:
    def __init__(self):
        self.main_exit_listeners = []

    def add_main_exit_event_listener(self, listener):
        self.main_exit_listeners.append(listener)

    def trigger_main_exit_event(self):
        for listener in self.main_exit_listeners:
            listener()

events = Events()