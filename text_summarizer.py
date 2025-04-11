import numpy as np
import networkx as nx
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from typing import List, Dict, Tuple, Set
import re

# Download required NLTK resources (uncomment if not already downloaded)
# nltk.download('punkt')
# nltk.download('stopwords')

class TextSummarizer:
    def __init__(self, language: str = 'english', similarity_threshold: float = 0.8):
        """
        Initialize the TextSummarizer with a specific language.
        
        Args:
            language: Language for stopwords. Default is 'english'.
            similarity_threshold: Threshold for detecting duplicate sentences (0.0 to 1.0).
        """
        try:
            self.stop_words = set(stopwords.words(language))
        except:
            self.stop_words = set()
        self.similarity_threshold = similarity_threshold
        
    def _preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess the text by splitting it into sentences.
        
        Args:
            text: The input text to be summarized.
            
        Returns:
            List of sentences.
        """
        # Split text into sentences
        sentences = sent_tokenize(text)
        
        # Handle case where sentence tokenizer fails (e.g., with repeated short phrases)
        if len(sentences) <= 1 and len(text) > 50 and '.' in text:
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            # Add periods back
            sentences = [s + '.' for s in sentences]
            
        return sentences
    
    def _normalize_sentence(self, sentence: str) -> str:
        """
        Normalize a sentence by removing extra whitespace and converting to lowercase.
        
        Args:
            sentence: The sentence to normalize.
            
        Returns:
            Normalized sentence.
        """
        # Remove extra whitespace and convert to lowercase
        return re.sub(r'\s+', ' ', sentence.lower().strip())
    
    def _create_sentence_vectors(self, sentences: List[str]) -> List[Dict[str, int]]:
        """
        Create vectors for each sentence based on word frequencies.
        
        Args:
            sentences: List of sentences from the text.
            
        Returns:
            List of sentence vectors.
        """
        sentence_vectors = []
        
        for sentence in sentences:
            words = word_tokenize(sentence.lower())
            words = [w for w in words if w not in self.stop_words and w.isalnum()]
            
            # Create sentence vector based on word frequencies
            sentence_vector = {}
            for word in words:
                if word not in sentence_vector:
                    sentence_vector[word] = 1
                else:
                    sentence_vector[word] += 1
                    
            sentence_vectors.append(sentence_vector)
            
        return sentence_vectors
    
    def _calculate_similarity_matrix(self, sentence_vectors: List[Dict[str, int]]) -> np.ndarray:
        """
        Calculate similarity between sentence vectors using cosine similarity.
        
        Args:
            sentence_vectors: List of sentence vectors.
            
        Returns:
            Similarity matrix as numpy array.
        """
        num_sentences = len(sentence_vectors)
        similarity_matrix = np.zeros((num_sentences, num_sentences))
        
        for i in range(num_sentences):
            for j in range(num_sentences):
                if i != j:
                    similarity_matrix[i][j] = self._cosine_similarity(
                        sentence_vectors[i], 
                        sentence_vectors[j]
                    )
                    
        return similarity_matrix
    
    def _cosine_similarity(self, vec1: Dict[str, int], vec2: Dict[str, int]) -> float:
        """
        Calculate cosine similarity between two sentence vectors.
        
        Args:
            vec1: First sentence vector.
            vec2: Second sentence vector.
            
        Returns:
            Cosine similarity score.
        """
        # Check for empty vectors
        if not vec1 or not vec2:
            return 0.0
            
        # Find all unique words in both sentences
        all_words = set(vec1.keys()).union(set(vec2.keys()))
        
        # Calculate dot product and magnitudes
        dot_product = 0
        magnitude1 = 0
        magnitude2 = 0
        
        for word in all_words:
            v1 = vec1.get(word, 0)
            v2 = vec2.get(word, 0)
            
            dot_product += v1 * v2
            magnitude1 += v1 ** 2
            magnitude2 += v2 ** 2
            
        magnitude1 = np.sqrt(magnitude1)
        magnitude2 = np.sqrt(magnitude2)
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _exact_duplicate_check(self, sentences: List[str]) -> Tuple[List[str], List[int]]:
        """
        Remove exact duplicates from sentences using a more efficient approach.
        
        Args:
            sentences: List of original sentences.
            
        Returns:
            Tuple containing unique sentences and mapping to original indices.
        """
        unique_sentences = []
        original_indices = []
        seen = set()
        
        for i, sentence in enumerate(sentences):
            # Normalize the sentence before checking
            normalized = self._normalize_sentence(sentence)
            
            if normalized not in seen and normalized.strip():
                seen.add(normalized)
                unique_sentences.append(sentence)
                original_indices.append(i)
                
        return unique_sentences, original_indices
    
    def _remove_duplicate_sentences(self, sentences: List[str]) -> Tuple[List[str], List[int]]:
        """
        Remove duplicate or highly similar sentences from the text using a two-stage approach.
        
        Args:
            sentences: List of original sentences.
            
        Returns:
            Tuple containing filtered sentences and mapping to original indices.
        """
        # First stage: Remove exact duplicates efficiently
        unique_sentences, original_indices = self._exact_duplicate_check(sentences)
        
        # Second stage: Check for semantic similarity
        if len(unique_sentences) > 1:
            sentence_vectors = self._create_sentence_vectors(unique_sentences)
            filtered_sentences = []
            filtered_indices = []
            similarity_checked = set()
            
            for i, (sentence, vector) in enumerate(zip(unique_sentences, sentence_vectors)):
                is_duplicate = False
                
                # Check similarity with already filtered sentences
                for j in range(len(filtered_sentences)):
                    # Create a unique pair identifier
                    pair_id = f"{min(i, j)}_{max(i, j)}"
                    
                    # Only check if we haven't compared these sentences before
                    if pair_id not in similarity_checked:
                        similarity_checked.add(pair_id)
                        similarity = self._cosine_similarity(vector, sentence_vectors[filtered_indices[j]])
                        
                        if similarity >= self.similarity_threshold:
                            is_duplicate = True
                            break
                
                if not is_duplicate:
                    filtered_sentences.append(sentence)
                    filtered_indices.append(i)
                    
            # Map back to original indices
            final_indices = [original_indices[idx] for idx in filtered_indices]
            return filtered_sentences, final_indices
        
        return unique_sentences, original_indices
    
    def _rank_sentences(self, similarity_matrix: np.ndarray) -> Dict[int, float]:
        """
        Rank sentences using PageRank algorithm.
        
        Args:
            similarity_matrix: Matrix of sentence similarities.
            
        Returns:
            Dictionary mapping sentence indices to scores.
        """
        # Check if similarity matrix is valid
        if similarity_matrix.size == 0:
            return {}
            
        # Create graph from similarity matrix
        nx_graph = nx.from_numpy_array(similarity_matrix)
        
        # Apply PageRank algorithm
        try:
            scores = nx.pagerank(nx_graph)
        except:
            # Fallback if PageRank fails
            scores = {i: 1.0 for i in range(similarity_matrix.shape[0])}
        
        return scores
    
    def generate_summary(self, text: str, ratio: float = 0.3, min_sentences: int = 2, max_sentences: int = 10, 
                  remove_duplicates: bool = True) -> str:
        """
        Generate a summary of the input text.
        
        Args:
            text: The input text to summarize.
            ratio: The proportion of sentences to include in the summary (0.0 to 1.0).
            min_sentences: Minimum number of sentences in the summary.
            max_sentences: Maximum number of sentences in the summary.
            remove_duplicates: Whether to remove duplicate sentences before summarization.
            
        Returns:
            Summarized text.
        """
        # Check for empty text
        if not text or not text.strip():
            return ""
            
        # Preprocess text
        original_sentences = self._preprocess_text(text)
        
        if not original_sentences:
            return text
            
        if len(original_sentences) <= min_sentences:
            return text
        
        # Remove duplicate sentences if requested
        if remove_duplicates:
            sentences, original_indices_map = self._remove_duplicate_sentences(original_sentences)
            if len(sentences) <= min_sentences:
                return ' '.join(sentences)
        else:
            sentences = original_sentences
            original_indices_map = list(range(len(original_sentences)))
        
        # Handle case where we have no sentences after deduplication
        if not sentences:
            return original_sentences[0] if original_sentences else ""
            
        # Create sentence vectors
        sentence_vectors = self._create_sentence_vectors(sentences)
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(sentence_vectors)
        
        # Rank sentences
        sentence_scores = self._rank_sentences(similarity_matrix)
        
        # Determine number of sentences for the summary
        num_sentences = max(min_sentences, min(max_sentences, int(len(sentences) * ratio)))
        num_sentences = min(num_sentences, len(sentences))
        
        # Get top-ranked sentences
        ranked_sentences = sorted(((i, score) for i, score in sentence_scores.items()), 
                                 key=lambda x: x[1], reverse=True)
        
        top_sentence_indices = [idx for idx, _ in ranked_sentences[:num_sentences]]
        
        # Map back to original indices
        original_top_indices = [original_indices_map[idx] for idx in top_sentence_indices]
        original_top_indices.sort()  # Sort to maintain original order
        
        # Create summary
        summary = ' '.join([original_sentences[i] for i in original_top_indices])
        return summary
    
    def get_duplicate_statistics(self, text: str) -> Dict:
        """
        Get statistics about duplicate sentences in the text.
        
        Args:
            text: The input text to analyze.
            
        Returns:
            Dictionary with duplicate statistics.
        """
        original_sentences = self._preprocess_text(text)
        filtered_sentences, original_indices = self._remove_duplicate_sentences(original_sentences)
        
        duplicates = len(original_sentences) - len(filtered_sentences)
        
        return {
            "total_sentences": len(original_sentences),
            "unique_sentences": len(filtered_sentences),
            "duplicate_sentences": duplicates,
            "duplicate_percentage": round(duplicates / len(original_sentences) * 100, 2) if original_sentences else 0
        }
