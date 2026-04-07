"""
Pattern Recognition Engine - Anomaly detection and clustering
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from app.utils.logger import get_logger

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = get_logger(__name__)


class PatternRecognizer:
    """
    Pattern Recognition Engine for anomaly detection and clustering
    """
    
    def __init__(self):
        """Initialize pattern recognizer"""
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available. Pattern recognition features limited.")
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
    
    def detect_anomalies(
        self,
        numeric_matrix: np.ndarray,
        contamination: float = 0.1,
        random_state: int = 42
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in numeric data using Isolation Forest
        
        Args:
            numeric_matrix: 2D numpy array of numeric features
            contamination: Expected proportion of outliers (0.01 to 0.5)
            random_state: Random seed for reproducibility
            
        Returns:
            List of anomaly dictionaries with index, outlier flag, and score
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn required for anomaly detection")
            return []
        
        if len(numeric_matrix) == 0:
            return []
        
        try:
            # Ensure 2D array
            if numeric_matrix.ndim == 1:
                numeric_matrix = numeric_matrix.reshape(-1, 1)
            
            # Normalize data
            if self.scaler:
                numeric_matrix = self.scaler.fit_transform(numeric_matrix)
            
            # Fit Isolation Forest
            iso_forest = IsolationForest(
                n_estimators=100,
                contamination=contamination,
                random_state=random_state,
                n_jobs=-1
            )
            
            predictions = iso_forest.fit_predict(numeric_matrix)
            scores = iso_forest.decision_function(numeric_matrix)
            
            # Convert to list of dictionaries
            anomalies = []
            for i in range(len(predictions)):
                anomalies.append({
                    "index": int(i),
                    "outlier": bool(predictions[i] == -1),
                    "score": float(scores[i]),
                    "severity": "high" if scores[i] < -0.1 else "medium" if scores[i] < 0 else "low"
                })
            
            outlier_count = sum(1 for a in anomalies if a["outlier"])
            logger.info(f"Detected {outlier_count} anomalies out of {len(anomalies)} samples")
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return []
    
    def detect_clusters(
        self,
        numeric_matrix: np.ndarray,
        method: str = "dbscan",
        eps: float = 0.5,
        min_samples: int = 5,
        n_clusters: int = 3
    ) -> Dict[str, Any]:
        """
        Detect clusters in numeric data
        
        Args:
            numeric_matrix: 2D numpy array of numeric features
            method: Clustering method ("dbscan" or "kmeans")
            eps: DBSCAN eps parameter (for DBSCAN only)
            min_samples: DBSCAN min_samples parameter (for DBSCAN only)
            n_clusters: Number of clusters (for KMeans only)
            
        Returns:
            Dictionary with cluster labels and statistics
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn required for clustering")
            return {"labels": [], "method": method, "n_clusters": 0}
        
        if len(numeric_matrix) == 0:
            return {"labels": [], "method": method, "n_clusters": 0}
        
        try:
            # Ensure 2D array
            if numeric_matrix.ndim == 1:
                numeric_matrix = numeric_matrix.reshape(-1, 1)
            
            # Normalize data
            if self.scaler:
                numeric_matrix = self.scaler.fit_transform(numeric_matrix)
            
            if method.lower() == "dbscan":
                clusterer = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
                labels = clusterer.fit_predict(numeric_matrix)
                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                n_noise = list(labels).count(-1)
                
                result = {
                    "labels": labels.tolist(),
                    "method": "dbscan",
                    "n_clusters": int(n_clusters),
                    "n_noise": int(n_noise),
                    "eps": eps,
                    "min_samples": min_samples
                }
                
            elif method.lower() == "kmeans":
                clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                labels = clusterer.fit_predict(numeric_matrix)
                
                result = {
                    "labels": labels.tolist(),
                    "method": "kmeans",
                    "n_clusters": int(n_clusters),
                    "centroids": clusterer.cluster_centers_.tolist(),
                    "inertia": float(clusterer.inertia_)
                }
            else:
                raise ValueError(f"Unknown clustering method: {method}")
            
            logger.info(f"Detected {result['n_clusters']} clusters using {method}")
            return result
            
        except Exception as e:
            logger.error(f"Clustering error: {e}")
            return {"labels": [], "method": method, "n_clusters": 0, "error": str(e)}
    
    def detect_trends(
        self,
        time_series: np.ndarray,
        window_size: int = 5
    ) -> Dict[str, Any]:
        """
        Detect trends in time series data
        
        Args:
            time_series: 1D numpy array of time-ordered values
            window_size: Size of moving average window
            
        Returns:
            Dictionary with trend information
        """
        if len(time_series) < window_size:
            return {"trend": "insufficient_data", "slope": 0.0}
        
        try:
            # Calculate moving average
            moving_avg = np.convolve(time_series, np.ones(window_size)/window_size, mode='valid')
            
            # Calculate slope
            x = np.arange(len(moving_avg))
            slope = np.polyfit(x, moving_avg, 1)[0]
            
            # Determine trend direction
            if slope > 0.01:
                trend = "increasing"
            elif slope < -0.01:
                trend = "decreasing"
            else:
                trend = "stable"
            
            # Calculate volatility
            volatility = np.std(time_series)
            
            return {
                "trend": trend,
                "slope": float(slope),
                "volatility": float(volatility),
                "mean": float(np.mean(time_series)),
                "min": float(np.min(time_series)),
                "max": float(np.max(time_series))
            }
            
        except Exception as e:
            logger.error(f"Trend detection error: {e}")
            return {"trend": "error", "error": str(e)}
    
    def find_patterns(
        self,
        data: List[Dict[str, Any]],
        numeric_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Find patterns across multiple numeric fields
        
        Args:
            data: List of data dictionaries
            numeric_fields: List of field names to analyze
            
        Returns:
            Dictionary with pattern analysis results
        """
        if not data or not numeric_fields:
            return {"patterns": [], "anomalies": [], "clusters": {}}
        
        try:
            # Extract numeric matrix
            matrix = []
            for item in data:
                row = [float(item.get(field, 0)) for field in numeric_fields]
                matrix.append(row)
            
            numeric_matrix = np.array(matrix)
            
            # Run analyses
            anomalies = self.detect_anomalies(numeric_matrix)
            clusters = self.detect_clusters(numeric_matrix)
            
            # Detect trends for each field
            trends = {}
            for i, field in enumerate(numeric_fields):
                time_series = numeric_matrix[:, i]
                trends[field] = self.detect_trends(time_series)
            
            return {
                "patterns": {
                    "field_trends": trends,
                    "cluster_analysis": clusters
                },
                "anomalies": anomalies,
                "clusters": clusters,
                "summary": {
                    "total_samples": len(data),
                    "n_outliers": sum(1 for a in anomalies if a["outlier"]),
                    "n_clusters": clusters.get("n_clusters", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Pattern finding error: {e}")
            return {"patterns": [], "anomalies": [], "clusters": {}, "error": str(e)}

