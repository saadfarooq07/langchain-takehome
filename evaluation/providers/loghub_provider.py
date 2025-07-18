"""LogHub dataset provider for evaluation framework."""

import os
import json
import tarfile
import zipfile
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
# import pandas as pd  # Commented out - only needed when actually loading LogHub datasets
import numpy as np
from urllib.parse import urlparse
import requests
from tqdm import tqdm

from ..core.interfaces import DatasetProvider, LogEntry, SystemType


class LogHubProvider(DatasetProvider):
    """Dataset provider for LogHub datasets."""
    
    LOGHUB_DATASETS = {
        "Android": {
            "system_type": SystemType.MOBILE,
            "file_name": "Android.tar.gz",
            "zenodo_id": "3227177",
            "description": "Mobile system logs from Android devices"
        },
        "Apache": {
            "system_type": SystemType.SERVER,
            "file_name": "Apache.tar.gz", 
            "zenodo_id": "3227177",
            "description": "Apache web server logs"
        },
        "BGL": {
            "system_type": SystemType.SUPERCOMPUTER,
            "file_name": "BGL.tar.gz",
            "zenodo_id": "3227177", 
            "description": "Blue Gene/L supercomputer logs"
        },
        "Hadoop": {
            "system_type": SystemType.DISTRIBUTED,
            "file_name": "Hadoop.tar.gz",
            "zenodo_id": "3227177",
            "description": "Hadoop distributed computing framework logs"
        },
        "HDFS": {
            "system_type": SystemType.DISTRIBUTED,
            "file_name": "HDFS_1.tar.gz",
            "zenodo_id": "3227177",
            "description": "Hadoop Distributed File System logs"
        },
        "HealthApp": {
            "system_type": SystemType.STANDALONE,
            "file_name": "HealthApp.tar.gz",
            "zenodo_id": "3227177",
            "description": "Health application logs"
        },
        "HPC": {
            "system_type": SystemType.SUPERCOMPUTER,
            "file_name": "HPC.tar.gz",
            "zenodo_id": "3227177",
            "description": "High Performance Computing cluster logs"
        },
        "Linux": {
            "system_type": SystemType.OS,
            "file_name": "Linux.tar.gz",
            "zenodo_id": "3227177",
            "description": "Linux system logs"
        },
        "Mac": {
            "system_type": SystemType.OS,
            "file_name": "Mac.tar.gz",
            "zenodo_id": "3227177",
            "description": "macOS system logs"
        },
        "OpenStack": {
            "system_type": SystemType.DISTRIBUTED,
            "file_name": "OpenStack.tar.gz",
            "zenodo_id": "3227177",
            "description": "OpenStack cloud platform logs"
        },
        "Proxifier": {
            "system_type": SystemType.STANDALONE,
            "file_name": "Proxifier.tar.gz",
            "zenodo_id": "3227177",
            "description": "Proxifier network proxy logs"
        },
        "Spark": {
            "system_type": SystemType.DISTRIBUTED,
            "file_name": "Spark.tar.gz",
            "zenodo_id": "3227177",
            "description": "Apache Spark distributed computing logs"
        },
        "SSH": {
            "system_type": SystemType.SERVER,
            "file_name": "SSH.tar.gz",
            "zenodo_id": "3227177",
            "description": "SSH server logs"
        },
        "Thunderbird": {
            "system_type": SystemType.SUPERCOMPUTER,
            "file_name": "Thunderbird.tar.gz",
            "zenodo_id": "3227177",
            "description": "Thunderbird supercomputer logs"
        },
        "Windows": {
            "system_type": SystemType.OS,
            "file_name": "Windows.tar.gz",
            "zenodo_id": "3227177",
            "description": "Windows system logs"
        },
        "Zookeeper": {
            "system_type": SystemType.DISTRIBUTED,
            "file_name": "Zookeeper.tar.gz",
            "zenodo_id": "3227177",
            "description": "Apache Zookeeper distributed coordination logs"
        }
    }
    
    def __init__(self, dataset_name: str, data_dir: str = "data/loghub", cache_dir: str = "cache"):
        """Initialize LogHub dataset provider.
        
        Args:
            dataset_name: Name of the LogHub dataset to load
            data_dir: Directory to store downloaded datasets
            cache_dir: Directory for caching processed data
        """
        if dataset_name not in self.LOGHUB_DATASETS:
            raise ValueError(f"Unknown dataset: {dataset_name}. Available: {list(self.LOGHUB_DATASETS.keys())}")
        
        self.dataset_name = dataset_name
        self.dataset_info = self.LOGHUB_DATASETS[dataset_name]
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        
        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._samples_cache: Optional[List[LogEntry]] = None
        self._metadata_cache: Optional[Dict[str, Any]] = None
    
    def get_name(self) -> str:
        """Get the name of the dataset provider."""
        return f"LogHub-{self.dataset_name}"
    
    def get_system_types(self) -> List[SystemType]:
        """Get the system types supported by this provider."""
        return [self.dataset_info["system_type"]]
    
    def _download_dataset(self, force_download: bool = False) -> Path:
        """Download dataset from Zenodo if not already present."""
        file_path = self.data_dir / self.dataset_info["file_name"]
        
        if file_path.exists() and not force_download:
            return file_path
        
        zenodo_url = f"https://zenodo.org/records/{self.dataset_info['zenodo_id']}/files/{self.dataset_info['file_name']}"
        
        print(f"Downloading {self.dataset_name} dataset from Zenodo...")
        
        try:
            response = requests.get(zenodo_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(file_path, 'wb') as f, tqdm(
                desc=self.dataset_info["file_name"],
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as progress_bar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))
            
            print(f"Downloaded {self.dataset_name} dataset to {file_path}")
            return file_path
            
        except Exception as e:
            print(f"Error downloading dataset: {e}")
            print(f"Please manually download {self.dataset_info['file_name']} from:")
            print(f"https://zenodo.org/records/{self.dataset_info['zenodo_id']}")
            print(f"And place it in {self.data_dir}")
            raise
    
    def _extract_dataset(self, archive_path: Path) -> Path:
        """Extract the dataset archive."""
        extract_dir = self.data_dir / f"{self.dataset_name}_extracted"
        
        if extract_dir.exists():
            return extract_dir
        
        print(f"Extracting {archive_path}...")
        
        if archive_path.suffix == '.gz':
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(self.data_dir)
        elif archive_path.suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(self.data_dir)
        else:
            raise ValueError(f"Unsupported archive format: {archive_path.suffix}")
        
        # Find the extracted directory
        for item in self.data_dir.iterdir():
            if item.is_dir() and item.name != "cache" and self.dataset_name.lower() in item.name.lower():
                if item != extract_dir:
                    item.rename(extract_dir)
                return extract_dir
        
        raise FileNotFoundError(f"Could not find extracted directory for {self.dataset_name}")
    
    def _load_log_file(self, log_file: Path) -> List[str]:
        """Load log entries from a log file."""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(log_file, 'r', encoding='latin1') as f:
                lines = f.readlines()
        
        # Clean up lines
        lines = [line.strip() for line in lines if line.strip()]
        return lines
    
    def _parse_structured_csv(self, csv_file: Path) -> List[Dict[str, Any]]:
        """Parse structured CSV file with log templates."""
        try:
            # df = pd.read_csv(csv_file)  # Commented out - pandas not available
            raise NotImplementedError("CSV loading requires pandas. Install with: pip install pandas")
            return df.to_dict('records')
        except Exception as e:
            print(f"Warning: Could not parse {csv_file}: {e}")
            return []
    
    def _load_labels(self, extract_dir: Path) -> Dict[str, Any]:
        """Load labels if available."""
        labels = {}
        
        # Look for various label files
        label_files = [
            'anomaly_label.csv',
            'labels.csv', 
            'normal_label.csv',
            'abnormal_label.csv'
        ]
        
        for label_file in label_files:
            label_path = extract_dir / label_file
            if label_path.exists():
                try:
                    # df = pd.read_csv(label_path)  # Commented out - pandas not available
                    raise NotImplementedError("CSV loading requires pandas. Install with: pip install pandas")
                    labels[label_file] = df.to_dict('records')
                except Exception as e:
                    print(f"Warning: Could not load {label_file}: {e}")
        
        return labels
    
    def _process_dataset_specific(self, extract_dir: Path) -> Tuple[List[str], Dict[str, Any]]:
        """Process dataset-specific files and return log entries and metadata."""
        log_entries = []
        metadata = {}
        
        # Dataset-specific processing
        if self.dataset_name == "HDFS":
            # HDFS has multiple files and structured data
            log_file = extract_dir / "HDFS.log"
            if log_file.exists():
                log_entries = self._load_log_file(log_file)
            
            # Load structured data
            structured_file = extract_dir / "HDFS.log_structured.csv"
            if structured_file.exists():
                metadata["structured_data"] = self._parse_structured_csv(structured_file)
            
            # Load templates
            template_file = extract_dir / "HDFS.log_templates.csv"
            if template_file.exists():
                metadata["templates"] = self._parse_structured_csv(template_file)
        
        elif self.dataset_name == "BGL":
            # BGL has specific format
            log_file = extract_dir / "BGL.log"
            if log_file.exists():
                log_entries = self._load_log_file(log_file)
        
        else:
            # Generic processing - look for .log files
            log_files = list(extract_dir.glob("*.log"))
            if log_files:
                log_file = log_files[0]  # Use the first log file found
                log_entries = self._load_log_file(log_file)
        
        # Load labels if available
        labels = self._load_labels(extract_dir)
        if labels:
            metadata["labels"] = labels
        
        return log_entries, metadata
    
    def load_samples(self, limit: Optional[int] = None) -> List[LogEntry]:
        """Load log samples from the dataset."""
        if self._samples_cache is not None and limit is None:
            return self._samples_cache
        
        # Download and extract dataset
        archive_path = self._download_dataset()
        extract_dir = self._extract_dataset(archive_path)
        
        # Process dataset
        log_entries, metadata = self._process_dataset_specific(extract_dir)
        
        # Convert to LogEntry objects
        samples = []
        for i, content in enumerate(log_entries):
            if limit is not None and i >= limit:
                break
            
            # Create metadata for this entry
            entry_metadata = {
                "index": i,
                "dataset": self.dataset_name,
                "source_file": str(extract_dir)
            }
            
            # Add any additional metadata
            if "structured_data" in metadata and i < len(metadata["structured_data"]):
                entry_metadata.update(metadata["structured_data"][i])
            
            sample = LogEntry(
                content=content,
                system_type=self.dataset_info["system_type"],
                dataset=self.dataset_name,
                metadata=entry_metadata
            )
            samples.append(sample)
        
        # Cache if no limit was specified
        if limit is None:
            self._samples_cache = samples
            self._metadata_cache = metadata
        
        return samples
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the dataset."""
        if self._metadata_cache is None:
            # Load samples to populate metadata cache
            self.load_samples(limit=1)
        
        # Download and extract dataset to get full metadata
        archive_path = self._download_dataset()
        extract_dir = self._extract_dataset(archive_path)
        _, metadata = self._process_dataset_specific(extract_dir)
        
        # Basic metadata
        result = {
            "name": self.dataset_name,
            "description": self.dataset_info["description"],
            "system_type": self.dataset_info["system_type"].value,
            "source": "LogHub",
            "zenodo_id": self.dataset_info["zenodo_id"],
            "data_directory": str(extract_dir),
            "has_labels": "labels" in metadata,
            "has_templates": "templates" in metadata,
            "has_structured_data": "structured_data" in metadata
        }
        
        # Add specific metadata
        result.update(metadata)
        
        return result


class LogHubMultiProvider(DatasetProvider):
    """Provider that can load multiple LogHub datasets."""
    
    def __init__(self, dataset_names: List[str], data_dir: str = "data/loghub", cache_dir: str = "cache"):
        """Initialize multi-dataset provider.
        
        Args:
            dataset_names: List of LogHub dataset names to load
            data_dir: Directory to store downloaded datasets
            cache_dir: Directory for caching processed data
        """
        self.dataset_names = dataset_names
        self.providers = [
            LogHubProvider(name, data_dir, cache_dir) 
            for name in dataset_names
        ]
    
    def get_name(self) -> str:
        """Get the name of the dataset provider."""
        return f"LogHub-Multi-{'-'.join(self.dataset_names)}"
    
    def get_system_types(self) -> List[SystemType]:
        """Get the system types supported by this provider."""
        system_types = set()
        for provider in self.providers:
            system_types.update(provider.get_system_types())
        return list(system_types)
    
    def load_samples(self, limit: Optional[int] = None) -> List[LogEntry]:
        """Load log samples from all datasets."""
        all_samples = []
        
        for provider in self.providers:
            samples = provider.load_samples()
            all_samples.extend(samples)
        
        if limit is not None:
            all_samples = all_samples[:limit]
        
        return all_samples
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about all datasets."""
        metadata = {
            "name": self.get_name(),
            "dataset_count": len(self.dataset_names),
            "datasets": self.dataset_names,
            "source": "LogHub",
            "system_types": [st.value for st in self.get_system_types()],
            "individual_metadata": {}
        }
        
        for provider in self.providers:
            metadata["individual_metadata"][provider.dataset_name] = provider.get_metadata()
        
        return metadata