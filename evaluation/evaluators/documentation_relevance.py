"""Documentation relevance evaluator for log analysis recommendations."""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from ..core.interfaces import Evaluator, EvaluationMetric, EvaluationResult, SystemType


class DocumentationRelevanceEvaluator(Evaluator):
    """Evaluates the relevance and quality of documentation references in analysis."""
    
    def __init__(self, 
                 trusted_domains: Optional[List[str]] = None,
                 relevance_keywords: Optional[Dict[str, List[str]]] = None):
        """Initialize the evaluator.
        
        Args:
            trusted_domains: List of trusted documentation domains
            relevance_keywords: Keywords that indicate relevance for different topics
        """
        self.trusted_domains = trusted_domains or [
            "docs.python.org",
            "docs.oracle.com",
            "docs.microsoft.com",
            "docs.aws.amazon.com",
            "kubernetes.io",
            "docker.com",
            "nginx.org",
            "apache.org",
            "postgresql.org",
            "mysql.com",
            "redis.io",
            "mongodb.com",
            "stackoverflow.com",
            "github.com",
            "gitlab.com"
        ]
        
        self.relevance_keywords = relevance_keywords or {
            "error": ["error", "exception", "troubleshooting", "debugging", "fix", "solve"],
            "performance": ["performance", "optimization", "tuning", "scaling", "memory", "cpu"],
            "configuration": ["config", "settings", "setup", "install", "configure"],
            "security": ["security", "authentication", "authorization", "ssl", "tls", "encryption"],
            "network": ["network", "connectivity", "firewall", "proxy", "load", "balance"],
            "database": ["database", "sql", "query", "transaction", "backup", "restore"]
        }
    
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        return "DocumentationRelevance"
    
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        return True  # Documentation relevance applies to all system types
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return "Evaluates the relevance and quality of documentation references in log analysis recommendations"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the documentation relevance.
        
        Args:
            outputs: Analysis outputs from the system
            reference: Reference data including log content and expected issues
            
        Returns:
            EvaluationMetric with documentation relevance score
        """
        # Extract analysis result
        analysis_result = outputs.get("analysis_result", {})
        
        # Extract documentation references
        doc_references = self._extract_documentation_references(analysis_result)
        
        if not doc_references:
            # No documentation references found
            return EvaluationMetric(
                key="documentation_relevance",
                value=0,
                score=0.0,
                comment="No documentation references found",
                result=EvaluationResult.FAILED
            )
        
        # Evaluate each reference
        relevance_scores = []
        quality_scores = []
        
        for doc_ref in doc_references:
            relevance_score = self._evaluate_reference_relevance(doc_ref, analysis_result, reference)
            quality_score = self._evaluate_reference_quality(doc_ref)
            
            relevance_scores.append(relevance_score)
            quality_scores.append(quality_score)
        
        # Calculate overall scores
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Combined score (weighted)
        overall_score = 0.7 * avg_relevance + 0.3 * avg_quality
        
        # Determine result
        if overall_score >= 0.8:
            result = EvaluationResult.PASSED
        elif overall_score >= 0.6:
            result = EvaluationResult.PARTIAL
        else:
            result = EvaluationResult.FAILED
        
        # Create comment
        comment = self._create_documentation_comment(
            doc_references, avg_relevance, avg_quality, overall_score
        )
        
        return EvaluationMetric(
            key="documentation_relevance",
            value=len(doc_references),
            score=overall_score,
            comment=comment,
            result=result
        )
    
    def _extract_documentation_references(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract documentation references from analysis result."""
        doc_references = []
        
        # Check recommendations for documentation
        recommendations = analysis_result.get("recommendations", [])
        for rec in recommendations:
            if isinstance(rec, dict):
                # Check for documentation URLs
                if "documentation" in rec:
                    doc_info = rec["documentation"]
                    if isinstance(doc_info, list):
                        for doc in doc_info:
                            doc_references.append({
                                "url": doc.get("url", ""),
                                "title": doc.get("title", ""),
                                "description": doc.get("description", ""),
                                "context": rec.get("description", "")
                            })
                    elif isinstance(doc_info, dict):
                        doc_references.append({
                            "url": doc_info.get("url", ""),
                            "title": doc_info.get("title", ""),
                            "description": doc_info.get("description", ""),
                            "context": rec.get("description", "")
                        })
                
                # Check for URLs in description
                description = rec.get("description", "")
                urls = self._extract_urls_from_text(description)
                for url in urls:
                    doc_references.append({
                        "url": url,
                        "title": "",
                        "description": "",
                        "context": description
                    })
        
        # Check for documentation in other fields
        for field in ["documentation", "references", "links"]:
            if field in analysis_result:
                field_data = analysis_result[field]
                if isinstance(field_data, list):
                    for item in field_data:
                        if isinstance(item, dict):
                            doc_references.append({
                                "url": item.get("url", ""),
                                "title": item.get("title", ""),
                                "description": item.get("description", ""),
                                "context": ""
                            })
                        elif isinstance(item, str):
                            urls = self._extract_urls_from_text(item)
                            for url in urls:
                                doc_references.append({
                                    "url": url,
                                    "title": "",
                                    "description": "",
                                    "context": item
                                })
        
        return doc_references
    
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text."""
        # URL regex pattern
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?'
        urls = re.findall(url_pattern, text)
        return urls
    
    def _evaluate_reference_relevance(self, doc_ref: Dict[str, Any], analysis_result: Dict[str, Any], reference: Dict[str, Any]) -> float:
        """Evaluate the relevance of a documentation reference."""
        relevance_score = 0.0
        
        # Extract context about the issues
        issues = analysis_result.get("issues", [])
        log_content = reference.get("log_content", "")
        
        # Determine the topic/category of the issues
        issue_topics = self._identify_issue_topics(issues, log_content)
        
        # Check if the documentation is relevant to the identified topics
        doc_url = doc_ref.get("url", "")
        doc_title = doc_ref.get("title", "")
        doc_description = doc_ref.get("description", "")
        doc_context = doc_ref.get("context", "")
        
        # Combine all documentation text
        doc_text = f"{doc_url} {doc_title} {doc_description} {doc_context}".lower()
        
        # Check relevance to identified topics
        for topic in issue_topics:
            if topic in self.relevance_keywords:
                keywords = self.relevance_keywords[topic]
                keyword_matches = sum(1 for keyword in keywords if keyword in doc_text)
                if keyword_matches > 0:
                    relevance_score += 0.3 * (keyword_matches / len(keywords))
        
        # Check URL relevance
        if doc_url:
            url_relevance = self._evaluate_url_relevance(doc_url, issue_topics)
            relevance_score += 0.4 * url_relevance
        
        # Check contextual relevance
        if doc_context:
            context_relevance = self._evaluate_contextual_relevance(doc_context, issues)
            relevance_score += 0.3 * context_relevance
        
        return min(1.0, relevance_score)
    
    def _evaluate_reference_quality(self, doc_ref: Dict[str, Any]) -> float:
        """Evaluate the quality of a documentation reference."""
        quality_score = 0.0
        
        doc_url = doc_ref.get("url", "")
        doc_title = doc_ref.get("title", "")
        doc_description = doc_ref.get("description", "")
        
        # Check if URL is from trusted domain
        if doc_url:
            parsed_url = urlparse(doc_url)
            domain = parsed_url.netloc.lower()
            
            # Remove www prefix
            if domain.startswith("www."):
                domain = domain[4:]
            
            is_trusted = any(trusted in domain for trusted in self.trusted_domains)
            if is_trusted:
                quality_score += 0.4
            else:
                quality_score += 0.1  # Some credit for having a URL
        
        # Check if title is provided and meaningful
        if doc_title:
            if len(doc_title) > 5:  # Meaningful title
                quality_score += 0.2
        
        # Check if description is provided and meaningful
        if doc_description:
            if len(doc_description) > 10:  # Meaningful description
                quality_score += 0.2
        
        # Check URL structure quality
        if doc_url:
            url_quality = self._evaluate_url_quality(doc_url)
            quality_score += 0.2 * url_quality
        
        return min(1.0, quality_score)
    
    def _identify_issue_topics(self, issues: List[Dict], log_content: str) -> List[str]:
        """Identify the main topics/categories of issues."""
        topics = set()
        
        # Analyze issues
        for issue in issues:
            issue_text = str(issue).lower()
            
            for topic, keywords in self.relevance_keywords.items():
                if any(keyword in issue_text for keyword in keywords):
                    topics.add(topic)
        
        # Analyze log content
        log_lower = log_content.lower()
        for topic, keywords in self.relevance_keywords.items():
            if any(keyword in log_lower for keyword in keywords):
                topics.add(topic)
        
        return list(topics)
    
    def _evaluate_url_relevance(self, url: str, issue_topics: List[str]) -> float:
        """Evaluate how relevant a URL is to the issue topics."""
        url_lower = url.lower()
        relevance_score = 0.0
        
        # Check if URL path contains relevant terms
        for topic in issue_topics:
            if topic in url_lower:
                relevance_score += 0.3
            
            # Check for topic-specific keywords in URL
            if topic in self.relevance_keywords:
                keywords = self.relevance_keywords[topic]
                keyword_matches = sum(1 for keyword in keywords if keyword in url_lower)
                if keyword_matches > 0:
                    relevance_score += 0.2 * (keyword_matches / len(keywords))
        
        return min(1.0, relevance_score)
    
    def _evaluate_contextual_relevance(self, context: str, issues: List[Dict]) -> float:
        """Evaluate how relevant the context is to the issues."""
        context_lower = context.lower()
        relevance_score = 0.0
        
        for issue in issues:
            issue_text = str(issue).lower()
            
            # Extract key terms from issue
            issue_terms = set(re.findall(r'\b\w+\b', issue_text))
            context_terms = set(re.findall(r'\b\w+\b', context_lower))
            
            # Remove common words
            stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
            issue_terms -= stopwords
            context_terms -= stopwords
            
            # Calculate term overlap
            if issue_terms and context_terms:
                overlap = len(issue_terms & context_terms)
                union = len(issue_terms | context_terms)
                similarity = overlap / union if union > 0 else 0
                relevance_score += similarity
        
        return min(1.0, relevance_score / len(issues)) if issues else 0.0
    
    def _evaluate_url_quality(self, url: str) -> float:
        """Evaluate the quality of a URL structure."""
        quality_score = 0.0
        
        parsed_url = urlparse(url)
        
        # Check if URL is well-formed
        if parsed_url.scheme and parsed_url.netloc:
            quality_score += 0.3
        
        # Check for HTTPS
        if parsed_url.scheme == "https":
            quality_score += 0.2
        
        # Check for meaningful path
        if parsed_url.path and len(parsed_url.path) > 1:
            quality_score += 0.2
        
        # Check for specific documentation indicators
        path_lower = parsed_url.path.lower()
        doc_indicators = ["doc", "documentation", "guide", "tutorial", "manual", "reference"]
        if any(indicator in path_lower for indicator in doc_indicators):
            quality_score += 0.3
        
        return min(1.0, quality_score)
    
    def _create_documentation_comment(self, doc_references: List[Dict], avg_relevance: float, avg_quality: float, overall_score: float) -> str:
        """Create a comment about documentation relevance."""
        comments = []
        
        comments.append(f"References Found: {len(doc_references)}")
        comments.append(f"Avg Relevance: {avg_relevance:.3f}")
        comments.append(f"Avg Quality: {avg_quality:.3f}")
        
        # Count trusted domains
        trusted_count = 0
        for doc_ref in doc_references:
            url = doc_ref.get("url", "")
            if url:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                if any(trusted in domain for trusted in self.trusted_domains):
                    trusted_count += 1
        
        comments.append(f"Trusted Sources: {trusted_count}")
        
        if overall_score >= 0.8:
            performance = "Excellent"
        elif overall_score >= 0.6:
            performance = "Good"
        elif overall_score >= 0.4:
            performance = "Fair"
        else:
            performance = "Poor"
        
        return f"{performance} documentation relevance. {' | '.join(comments)}"