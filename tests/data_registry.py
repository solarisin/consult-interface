from pathlib import Path

class DataEntry:
    def __init__(self, name: str, command: bytes, capture_file: Path, metadata: dict = None):
        self.name = name
        self.command = command
        self.capture_file = capture_file
        self.metadata = metadata

class DataRegistry:
    Registry = None
    def __init__(self):
        self.data = {}

    def add(self, name: str, command: bytes, capture_file: Path, metadata: dict = None):
        """
        Add a data file entry to the registry
        :param name: Identifier for the data entry (dict key)
        :param command: The command bytes to be sent to the ECU which generated the capture file
        :param capture_file: Path to the file containing the captured data
        :param metadata: Optional metadata to be associated with the data entry
        :return: None
        """
        if len(command) > 0 and capture_file.exists():
            self.data[name] = DataEntry(name, command, capture_file, metadata)
        else:
            raise ValueError("Invalid command or file path")

    def get(self, name) -> DataEntry | None:
        if name not in self.data:
            return None
        return self.data[name]

    def get_names(self):
        return list(self.data.keys())

    @staticmethod
    def generate_registry(project_root_path):
        DataRegistry.Registry = DataRegistry()
        DataRegistry.Registry.add("test_1", b'\xD0', Path(project_root_path, 'docs', 'test_data.hex'))

    @staticmethod
    def get_registry(project_root_path = None) -> 'DataRegistry':
        # generate the registry if it doesn't exist and a project root path is provided
        if DataRegistry.Registry is None:
            if project_root_path is None:
                raise ValueError("DataRegistry not initialized")
            DataRegistry.generate_registry(project_root_path)
        return DataRegistry.Registry
