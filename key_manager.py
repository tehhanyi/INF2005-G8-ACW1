import hashlib
import struct
from typing import Tuple, List

class KeyManager:
    """
    Manages custom key format for LSB steganography.
    Key format influences bit selection, starting position, and permutation.
    """
    
    def __init__(self, key: str):
        """
        Initialize key manager with user-provided key.
        
        Args:
            key: User-provided key (can be numeric or string)
        """
        self.original_key = str(key)
        self.key_hash = hashlib.sha256(self.original_key.encode()).digest()
        
        # Extract key components from hash
        self._parse_key_components()
    
    def _parse_key_components(self):
        """Parse key hash into meaningful components for steganography."""
        # Use first 4 bytes for starting position seed
        self.position_seed = struct.unpack('>I', self.key_hash[:4])[0]
        
        # Use next 4 bytes for bit permutation seed
        self.permutation_seed = struct.unpack('>I', self.key_hash[4:8])[0]
        
        # Use next byte for starting bit offset (0-7)
        self.bit_offset = self.key_hash[8] % 8
        
        # Use next 4 bytes for step size seed
        self.step_seed = struct.unpack('>I', self.key_hash[12:16])[0]
        
        # Generate bit permutation table (for reordering bits within bytes)
        self.bit_permutation = self._generate_bit_permutation()
    
    def _generate_bit_permutation(self) -> List[int]:
        """Generate a permutation of bit positions (0-7) based on key."""
        bits = list(range(8))
        # Use permutation seed to shuffle bit positions
        seed = self.permutation_seed
        for i in range(len(bits)):
            j = (seed + i) % len(bits)
            bits[i], bits[j] = bits[j], bits[i]
            seed = (seed * 1103515245 + 12345) & 0x7fffffff  # Linear congruential generator
        return bits
    
    def get_starting_position(self, data_length: int) -> int:
        """Get starting position in cover data based on key."""
        if data_length <= 1:
            return 0
        return self.position_seed % (data_length // 2)  # Start in first half
    
    def get_step_size(self, data_length: int) -> int:
        """Get step size for traversing cover data."""
        # Ensure step size is reasonable and doesn't skip too much data
        base_step = max(1, (self.step_seed % 5) + 1)  # Step size between 1-5
        return base_step
    
    def permute_byte_bits(self, byte_value: int, reverse: bool = False) -> int:
        """
        Permute bits within a byte based on key.
        
        Args:
            byte_value: The byte value to permute
            reverse: If True, reverse the permutation
            
        Returns:
            Permuted byte value
        """
        if reverse:
            # Create reverse permutation
            reverse_perm = [0] * 8
            for i, pos in enumerate(self.bit_permutation):
                reverse_perm[pos] = i
            perm = reverse_perm
        else:
            perm = self.bit_permutation
        
        result = 0
        for i in range(8):
            if byte_value & (1 << i):
                result |= (1 << perm[i])
        
        return result
    
    def get_metadata(self) -> dict:
        """Get key metadata for validation during decoding."""
        return {
            'key_hash': self.key_hash.hex()[:16],  # First 16 chars of hex hash
            'bit_offset': self.bit_offset,
            'position_seed': self.position_seed & 0xFFFF,  # Lower 16 bits
            'step_seed': self.step_seed & 0xFFFF,  # Lower 16 bits
        }
    
    def validate_key(self, metadata: dict) -> bool:
        """Validate that the current key matches the metadata."""
        current_metadata = self.get_metadata()
        return (current_metadata['key_hash'] == metadata['key_hash'] and
                current_metadata['bit_offset'] == metadata['bit_offset'] and
                current_metadata['position_seed'] == metadata['position_seed'] and
                current_metadata['step_seed'] == metadata['step_seed'])