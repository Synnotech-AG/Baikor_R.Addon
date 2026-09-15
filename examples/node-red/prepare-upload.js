// Function node: two outputs (HTTP import request / safe failure summary).
if (msg.statusCode !== 200 || typeof msg.payload?.access_token !== 'string' || !msg.payload.access_token) {
    return [null, {payload: {ok: false, errorKey: 'integration.authenticationFailed'}}];
}
const baseUrl = env.get('BAIKOR_APP_URL');
if (!/^https:\/\/[^/?#]+\/?$/.test(baseUrl || '') || !Buffer.isBuffer(msg.trenchZip)) {
    return [null, {payload: {ok: false, errorKey: 'integration.configurationMissing'}}];
}
const token = msg.payload.access_token;
msg.method = 'POST';
msg.url = baseUrl.replace(/\/$/, '') + '/api/construction-sites/imports/trenches';
msg.followRedirects = false;
msg.requestTimeout = 120000;
// Replace response headers from the first HTTP node; never forward them wholesale.
msg.headers = {'content-type': 'multipart/form-data', authorization: 'Bearer ' + token};
msg.cookies = {};
msg.payload = {
    file: {value: msg.trenchZip, options: {filename: msg.importFileName, contentType: 'application/zip'}},
    bufferMetres: '1'
};
delete msg.trenchZip;
return [msg, null];
