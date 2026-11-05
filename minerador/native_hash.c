#include <stdint.h>
#include <string.h>
#include <openssl/sha.h>

/* Retorna 1 quando encontra nonce válido, 0 quando esgota o lote. */
int scan_nonces(const unsigned char *prefix, const unsigned char *target,
                uint32_t start, uint32_t stride, uint32_t limit,
                uint32_t *found, uint32_t *processed) {
    if (!prefix || !target || !found || !processed || !stride) return -1;
    SHA256_CTX base, current;
    unsigned char first[SHA256_DIGEST_LENGTH], digest[SHA256_DIGEST_LENGTH];
    unsigned char nonce_bytes[4];
    SHA256_Init(&base);
    SHA256_Update(&base, prefix, 76);
    *processed = 0;
    for (uint32_t i = 0; i < limit; i++) {
        uint64_t candidate = (uint64_t)start + (uint64_t)i * stride;
        if (candidate > UINT32_MAX) break;
        uint32_t nonce = (uint32_t)candidate;
        nonce_bytes[0] = (unsigned char)nonce;
        nonce_bytes[1] = (unsigned char)(nonce >> 8);
        nonce_bytes[2] = (unsigned char)(nonce >> 16);
        nonce_bytes[3] = (unsigned char)(nonce >> 24);
        memcpy(&current, &base, sizeof(current));
        SHA256_Update(&current, nonce_bytes, 4);
        SHA256_Final(first, &current);
        SHA256(first, SHA256_DIGEST_LENGTH, digest);
        ++*processed;
        int cmp = 0;
        for (int j = SHA256_DIGEST_LENGTH - 1; j >= 0; j--) {
            if (digest[j] < target[j]) { cmp = -1; break; }
            if (digest[j] > target[j]) { cmp = 1; break; }
        }
        if (cmp <= 0) { *found = nonce; return 1; }
    }
    return 0;
}
