// Function node: two outputs (safe success summary / safe failure summary).
// Return NEW messages: drop headers, credentials, uploaded bytes and HTTP internals.
const result = msg.payload;
if (msg.statusCode === 200 && typeof result?.batchId === 'string') {
    return [{payload: {
        ok: true,
        batchId: result.batchId,
        createdCount: result.createdCount,
        skippedCount: result.skippedCount
    }}, null];
}
return [null, {payload: {
    ok: false,
    statusCode: msg.statusCode,
    errorKey: typeof result?.errorKey === 'string' ? result.errorKey : 'integration.importFailed'
}}];
