// Tests the exact pasteable Function-node examples without modifying any Node-RED instance.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const directory = path.join(__dirname, '..', 'examples', 'node-red');
const settings = {
    BAIKOR_TOKEN_URL: 'https://identity.example.invalid/realms/tenant/protocol/openid-connect/token',
    BAIKOR_APP_URL: 'https://baikor.example.invalid',
    BAIKOR_IMPORT_CLIENT_ID: 'example-import',
    BAIKOR_IMPORT_CLIENT_SECRET: 'test&secret=+not-real'
};
function run(name, msg, configuration = settings) {
    const source = fs.readFileSync(path.join(directory, name + '.js'), 'utf8');
    return vm.runInNewContext('(function () {\n' + source + '\n})()', {
        msg, Buffer, env: {get: key => configuration[key]}
    });
}
const zip = Buffer.from('synthetic fixture');
const [tokenRequest] = run('request-token', {payload: zip, filename: '/incoming/a file.zip'});
assert.equal(new URLSearchParams(tokenRequest.payload).get('client_secret'), settings.BAIKOR_IMPORT_CLIENT_SECRET);
assert.equal(tokenRequest.followRedirects, false);
assert.equal(tokenRequest.importFileName, 'a_file.zip');
assert.equal(tokenRequest.trenchZip, zip);
tokenRequest.statusCode = 200;
tokenRequest.payload = {access_token: 'test-access-token'};
tokenRequest.headers = {'set-cookie': 'must-not-forward'};
const [upload] = run('prepare-upload', tokenRequest);
assert.equal(upload.headers.authorization, 'Bearer test-access-token');
assert.equal(upload.headers['set-cookie'], undefined);
assert.equal(upload.payload.file.value, zip);
assert.equal(upload.followRedirects, false);
upload.payload = {batchId: 'test-batch', createdCount: 2, skippedCount: 1};
const [summary] = run('summarize-result', upload);
assert.equal(summary.payload.createdCount, 2);
assert.deepEqual(Object.keys(summary), ['payload']);
assert(!JSON.stringify(summary).includes('test-access-token'));
for (const statusCode of [302, 401, 403, 409, 500]) {
    const [success, failure] = run('summarize-result', {statusCode, payload: 'not JSON', headers: {authorization: 'secret'}});
    assert.equal(success, null);
    assert.equal(failure.payload.ok, false);
    assert(!JSON.stringify(failure).includes('secret'));
}
assert.equal(run('request-token', {payload: Buffer.alloc(0)})[1].payload.errorKey, 'integration.fileRequired');
assert.equal(run('request-token', {payload: Buffer.alloc(25 * 1024 * 1024 + 1)})[1].payload.errorKey, 'integration.fileTooLarge');
assert.equal(run('request-token', {payload: zip}, {})[1].payload.errorKey, 'integration.configurationMissing');
assert.equal(run('prepare-upload', {statusCode: 302, payload: {access_token: 'secret'}})[0], null);
assert.equal(run('prepare-upload', {statusCode: 200, payload: {access_token: 'secret'}, trenchZip: zip}, {...settings, BAIKOR_APP_URL: 'http://unsafe.invalid'})[0], null);
console.log('PASS: Node-RED examples preserve bytes, encode credentials, replace headers, reject redirects/configuration errors and emit credential-free summaries.');
