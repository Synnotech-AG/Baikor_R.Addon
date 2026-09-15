// Function node: two outputs (HTTP token request / safe failure summary).
function fail(errorKey) {
    return [null, {payload: {ok: false, errorKey}}];
}
if (!Buffer.isBuffer(msg.payload) || msg.payload.length === 0) {
    return fail('integration.fileRequired');
}
if (msg.payload.length > 25 * 1024 * 1024) {
    return fail('integration.fileTooLarge');
}
const tokenUrl = env.get('BAIKOR_TOKEN_URL');
const clientId = env.get('BAIKOR_IMPORT_CLIENT_ID');
const clientSecret = env.get('BAIKOR_IMPORT_CLIENT_SECRET');
if (!/^https:\/\/[^/]+\/realms\/[^/]+\/protocol\/openid-connect\/token$/.test(tokenUrl || '') || !clientId || !clientSecret) {
    return fail('integration.configurationMissing');
}
msg.trenchZip = msg.payload;
msg.importFileName = String(msg.filename || 'trenches.zip').split(/[\\/]/).pop().replace(/[^a-zA-Z0-9._-]/g, '_');
msg.method = 'POST';
msg.url = tokenUrl;
msg.followRedirects = false;
msg.requestTimeout = 30000;
msg.headers = {'content-type': 'application/x-www-form-urlencoded'};
msg.cookies = {};
msg.payload = 'grant_type=client_credentials&client_id=' + encodeURIComponent(clientId) +
    '&client_secret=' + encodeURIComponent(clientSecret);
return [msg, null];
