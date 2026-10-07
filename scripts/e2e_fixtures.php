<?php

declare(strict_types=1);

/**
 * Nesti E2E fixture helper — baked into the nesti-sandbox-e2e image as
 * /opt/nesti/e2e_fixtures.php and run by its CMD, with the Laravel workspace
 * as the current directory, before any frontend build or browser test.
 *
 * It replaces `php artisan migrate --force --seed` and adds one capability:
 * preparing the data an E2E suite declared in e2e/nesti-fixtures.json.
 *
 *   1. Validate the manifest with exactly the rules of e2e_fixtures.py.
 *   2. Boot the application; require the default connection and every
 *      declared model's connection to be the recreated workspace SQLite file.
 *   3. migrate --force, then db:seed --force (the default DatabaseSeeder).
 *   4. For each declaration, probe its GET endpoint through the HTTP kernel.
 *      Rows → satisfied.  No rows, a confirmed SELECT on the model's table and
 *      an empty table → run the declared seeder once and require rows.  If the
 *      seeder's class AND its conventional file are both absent, report it.
 *
 * Exit codes / report (/nesti-results/fixtures.json, written atomically):
 *   0  {"version":1,"status":"ready"}
 *   78 {"version":1,"status":"missing_seeder","requirement":{endpoint,model,seeder,table}}
 *   1  every other preparation or contract error — a message, no report.
 *
 * It never uses raw DDL, migrate:fresh, truncation or any database other than
 * the workspace SQLite file.
 */

use Illuminate\Contracts\Console\Kernel as ConsoleKernel;
use Illuminate\Contracts\Container\BindingResolutionException;
use Illuminate\Contracts\Http\Kernel as HttpKernel;
use Illuminate\Database\Connection;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Seeder;
use Illuminate\Foundation\Application;
use Illuminate\Http\Request;

const NESTI_MANIFEST_PATH = 'e2e/nesti-fixtures.json';
const NESTI_MANIFEST_MAX_BYTES = 32768;
const NESTI_MAX_FIXTURES = 16;
const NESTI_MAX_NAME_CHARS = 512;
const NESTI_MODEL_PREFIX = 'App\\Models\\';
const NESTI_SEEDER_PREFIX = 'Database\\Seeders\\';
const NESTI_RESULTS_DIR = '/nesti-results';
const NESTI_REPORT_FILENAME = 'fixtures.json';
const NESTI_REPORT_MAX_BYTES = 4096;
const NESTI_EXIT_READY = 0;
const NESTI_EXIT_FAILED = 1;
const NESTI_EXIT_MISSING_SEEDER = 78;
// The D modifier: `$` must not match before a trailing newline.
const NESTI_ENDPOINT_RE = '#^/api(/[A-Za-z0-9._~-]+)+$#D';
const NESTI_CLASS_RE = '/^[A-Za-z_][A-Za-z0-9_]*(\\\\[A-Za-z_][A-Za-z0-9_]*)+$/D';
const NESTI_TABLE_RE = '/^[A-Za-z_][A-Za-z0-9_]*$/D';

/** An ordinary preparation/contract failure: message, no report, exit 1. */
final class NestiFixtureError extends RuntimeException
{
}

function nesti_say(string $message): void
{
    fwrite(STDOUT, "[nesti-fixtures] {$message}\n");
}

function nesti_fail(string $message): never
{
    throw new NestiFixtureError($message);
}

// ─────────────────────────────────────────────────────────────────────────────
// Manifest validation (mirrors e2e_fixtures.parse_manifest / load_requirements)
// ─────────────────────────────────────────────────────────────────────────────

/** json_decode keeps the last of repeated keys; the contract rejects them. */
function nesti_assert_unique_keys(string $json): void
{
    $stack = [];
    $length = strlen($json);
    for ($i = 0; $i < $length; $i++) {
        $char = $json[$i];
        $top = count($stack) - 1;
        if ($char === '"') {
            $start = $i;
            for ($i++; $i < $length && $json[$i] !== '"'; $i++) {
                if ($json[$i] === '\\') {
                    $i++;
                }
            }
            if ($top >= 0 && $stack[$top]['object'] && $stack[$top]['expect_key']) {
                $key = json_decode(substr($json, $start, $i - $start + 1), false, 512, JSON_THROW_ON_ERROR);
                if (isset($stack[$top]['keys'][$key])) {
                    throw new JsonException('duplicate JSON key ' . json_encode($key, JSON_UNESCAPED_SLASHES));
                }
                $stack[$top]['keys'][$key] = true;
                $stack[$top]['expect_key'] = false;
            }
        } elseif ($char === '{') {
            $stack[] = ['object' => true, 'expect_key' => true, 'keys' => []];
        } elseif ($char === '[') {
            $stack[] = ['object' => false, 'expect_key' => false, 'keys' => []];
        } elseif ($char === '}' || $char === ']') {
            array_pop($stack);
        } elseif ($char === ',' && $top >= 0 && $stack[$top]['object']) {
            $stack[$top]['expect_key'] = true;
        }
    }
}

/** @return list<string> */
function nesti_object_keys(stdClass $object): array
{
    $keys = array_map('strval', array_keys(get_object_vars($object)));
    sort($keys, SORT_STRING);

    return $keys;
}

function nesti_too_long(string $value): bool
{
    return mb_strlen($value, 'UTF-8') > NESTI_MAX_NAME_CHARS;
}

function nesti_class_name(mixed $value, string $prefix, string $label): string
{
    if (!is_string($value) || $value === '' || nesti_too_long($value)) {
        nesti_fail("{$label} must be a class name of at most " . NESTI_MAX_NAME_CHARS . ' characters');
    }
    $quoted = json_encode($value, JSON_UNESCAPED_SLASHES);
    if (!str_starts_with($value, $prefix) || $value === $prefix) {
        nesti_fail("{$label} {$quoted} must start with " . json_encode($prefix));
    }
    if (preg_match(NESTI_CLASS_RE, $value) !== 1) {
        nesti_fail("{$label} {$quoted} is not an ASCII namespaced class name");
    }

    return $value;
}

function nesti_endpoint(mixed $value): string
{
    if (!is_string($value) || $value === '' || nesti_too_long($value)) {
        nesti_fail('endpoint must be a path of at most ' . NESTI_MAX_NAME_CHARS . ' characters');
    }
    $quoted = json_encode($value, JSON_UNESCAPED_SLASHES);
    if (preg_match(NESTI_ENDPOINT_RE, $value) !== 1) {
        nesti_fail("endpoint {$quoted} must be a local /api path (no URL, query or fragment)");
    }
    foreach (explode('/', $value) as $segment) {
        if ($segment === '.' || $segment === '..') {
            nesti_fail("endpoint {$quoted} must not contain '.' or '..' segments");
        }
    }

    return $value;
}

/** @return list<array{endpoint: string, model: string, seeder: string}> */
function nesti_parse_manifest(mixed $data): array
{
    if (!$data instanceof stdClass || nesti_object_keys($data) !== ['fixtures', 'version']) {
        nesti_fail('the manifest is an object with exactly "version" and "fixtures"');
    }
    if (!is_int($data->version) || $data->version !== 1) {
        nesti_fail('unsupported manifest version ' . json_encode($data->version) . ' (expected 1)');
    }
    $fixtures = $data->fixtures;
    if (!is_array($fixtures)) {
        nesti_fail('"fixtures" must be a list');
    }
    if (count($fixtures) > NESTI_MAX_FIXTURES) {
        nesti_fail('at most ' . NESTI_MAX_FIXTURES . ' fixtures may be declared, got ' . count($fixtures));
    }

    $requirements = [];
    $seen = [];
    foreach ($fixtures as $index => $entry) {
        try {
            if (!$entry instanceof stdClass) {
                nesti_fail('a fixture requirement must be a JSON object');
            }
            if (nesti_object_keys($entry) !== ['endpoint', 'model', 'seeder']) {
                nesti_fail('a fixture requirement has exactly the fields ["endpoint", "model", "seeder"]');
            }
            $requirement = [
                'endpoint' => nesti_endpoint($entry->endpoint),
                'model' => nesti_class_name($entry->model, NESTI_MODEL_PREFIX, 'model'),
                'seeder' => nesti_class_name($entry->seeder, NESTI_SEEDER_PREFIX, 'seeder'),
            ];
        } catch (NestiFixtureError $error) {
            nesti_fail("fixtures[{$index}]: {$error->getMessage()}");
        }
        $identity = json_encode(array_values($requirement), JSON_THROW_ON_ERROR);
        if (isset($seen[$identity])) {
            nesti_fail("fixtures[{$index}] repeats an earlier declaration");
        }
        $seen[$identity] = true;
        $requirements[] = $requirement;
    }

    return $requirements;
}

/** @return list<array{endpoint: string, model: string, seeder: string}> */
function nesti_load_requirements(string $root): array
{
    $path = $root . '/' . NESTI_MANIFEST_PATH;
    if (!file_exists($path) && !is_link($path)) {
        return [];
    }
    if (is_link($path) || !is_file($path)) {
        nesti_fail(NESTI_MANIFEST_PATH . ' must be a regular file');
    }
    $raw = file_get_contents($path, false, null, 0, NESTI_MANIFEST_MAX_BYTES + 1);
    if ($raw === false) {
        nesti_fail(NESTI_MANIFEST_PATH . ' is unreadable');
    }
    if (strlen($raw) > NESTI_MANIFEST_MAX_BYTES) {
        nesti_fail(NESTI_MANIFEST_PATH . ' exceeds ' . NESTI_MANIFEST_MAX_BYTES . ' bytes');
    }
    try {
        $data = json_decode($raw, false, 64, JSON_THROW_ON_ERROR);
        nesti_assert_unique_keys($raw);
    } catch (JsonException $error) {
        nesti_fail(NESTI_MANIFEST_PATH . " is not valid UTF-8 JSON: {$error->getMessage()}");
    }

    return nesti_parse_manifest($data);
}

// ─────────────────────────────────────────────────────────────────────────────
// Result transport
// ─────────────────────────────────────────────────────────────────────────────

function nesti_report_path(): string
{
    return NESTI_RESULTS_DIR . '/' . NESTI_REPORT_FILENAME;
}

/** Atomically publish a report: temp file in the result directory + rename. */
function nesti_write_report(array $report): void
{
    $json = json_encode($report, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
    if (strlen($json) > NESTI_REPORT_MAX_BYTES) {
        nesti_fail('the fixture report exceeds ' . NESTI_REPORT_MAX_BYTES . ' bytes');
    }
    if (!is_dir(NESTI_RESULTS_DIR) || !is_writable(NESTI_RESULTS_DIR)) {
        nesti_fail('result directory ' . NESTI_RESULTS_DIR . ' is missing or not writable');
    }
    $temporary = tempnam(NESTI_RESULTS_DIR, '.fixtures-');
    if ($temporary === false || dirname($temporary) !== NESTI_RESULTS_DIR) {
        if ($temporary !== false) {
            @unlink($temporary);
        }
        nesti_fail('cannot create a temporary report file in ' . NESTI_RESULTS_DIR);
    }
    // The runner reads the report as the (non-root) host user.
    if (file_put_contents($temporary, $json) !== strlen($json)
        || !chmod($temporary, 0644)
        || !rename($temporary, nesti_report_path())) {
        @unlink($temporary);
        nesti_fail('cannot write the fixture report ' . nesti_report_path());
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Application checks
// ─────────────────────────────────────────────────────────────────────────────

function nesti_assert_isolated(Connection $connection, string $expected, string $label): void
{
    $driver = $connection->getDriverName();
    $database = $connection->getConfig('database');
    $actual = is_string($database) && $database !== '' ? realpath($database) : false;
    if ($driver !== 'sqlite' || $actual !== $expected) {
        nesti_fail(sprintf(
            '%s (connection %s, driver %s, database %s) is not the recreated workspace SQLite file %s',
            $label,
            json_encode($connection->getName()),
            json_encode($driver),
            json_encode($database, JSON_UNESCAPED_SLASHES),
            $expected,
        ));
    }
}

function nesti_inside(string|false $file, string|false $directory): bool
{
    if ($file === false || $directory === false) {
        return false;
    }
    $real = realpath($file);

    return $real !== false && str_starts_with($real, $directory . '/');
}

function nesti_resolve_model(string $class, string $root, string $database): Model
{
    if (!class_exists($class)) {
        nesti_fail("declared model {$class} does not exist");
    }
    if (!is_subclass_of($class, Model::class)) {
        nesti_fail("declared model {$class} is not an Eloquent model");
    }
    $reflection = new ReflectionClass($class);
    if ($reflection->isAbstract()) {
        nesti_fail("declared model {$class} is abstract");
    }
    if (!nesti_inside($reflection->getFileName(), realpath($root . '/app/Models'))) {
        nesti_fail("declared model {$class} is not defined inside app/Models");
    }
    /** @var Model $model */
    $model = $reflection->newInstance();
    nesti_assert_isolated($model->getConnection(), $database, "declared model {$class}'s connection");

    return $model;
}

function nesti_seeder_file(string $root, string $seeder): string
{
    return $root . '/database/seeders/'
        . str_replace('\\', '/', substr($seeder, strlen(NESTI_SEEDER_PREFIX))) . '.php';
}

function nesti_present(string $path): bool
{
    return file_exists($path) || is_link($path);
}

/** Run an Artisan command, echoing its output even when it throws. */
function nesti_artisan(ConsoleKernel $console, string $command, array $parameters): int
{
    try {
        return $console->call($command, $parameters);
    } finally {
        try {
            $output = $console->output();
        } catch (Throwable) {
            $output = '';
        }
        if ($output !== '') {
            fwrite(STDOUT, rtrim($output) . "\n");
        }
    }
}

/**
 * The declared seeder a default-seed exception names, when that is the only
 * cause: Laravel's container could not reflect the class, and neither the
 * class nor its conventional file exists.  Anything else returns null.
 *
 * @param list<array{endpoint: string, model: string, seeder: string}> $requirements
 */
function nesti_unresolved_declared_seeder(Throwable $error, array $requirements, string $root): ?string
{
    if (!$error instanceof BindingResolutionException
        || !$error->getPrevious() instanceof ReflectionException) {
        return null;
    }
    foreach (array_unique(array_column($requirements, 'seeder')) as $seeder) {
        if ($error->getMessage() === "Target class [{$seeder}] does not exist."
            && !class_exists($seeder)
            && !nesti_present(nesti_seeder_file($root, $seeder))) {
            return $seeder;
        }
    }

    return null;
}

/** @return array{rows: int, queries: list<string>} */
function nesti_probe(Application $app, string $endpoint, Connection $connection): array
{
    $kernel = $app->make(HttpKernel::class);
    $request = Request::create($endpoint, 'GET', server: ['HTTP_ACCEPT' => 'application/json']);

    $connection->flushQueryLog();
    $connection->enableQueryLog();
    try {
        $response = $kernel->handle($request);
        $kernel->terminate($request, $response);
    } finally {
        $queries = array_values(array_filter(
            array_column($connection->getQueryLog(), 'query'),
            'is_string',
        ));
        $connection->disableQueryLog();
        $connection->flushQueryLog();
    }

    $status = $response->getStatusCode();
    $content = $response->getContent();
    if ($status !== 200) {
        $body = is_string($content) ? mb_strimwidth(trim($content), 0, 300, '…', 'UTF-8') : '';
        nesti_fail("GET {$endpoint} answered HTTP {$status}, expected 200" . ($body !== '' ? ": {$body}" : ''));
    }
    if (!is_string($content)) {
        nesti_fail("GET {$endpoint} did not return a JSON body");
    }
    try {
        $decoded = json_decode($content, false, 512, JSON_THROW_ON_ERROR);
    } catch (JsonException $error) {
        nesti_fail("GET {$endpoint} did not return JSON: {$error->getMessage()}");
    }
    if (is_array($decoded)) {
        $rows = count($decoded);
    } elseif ($decoded instanceof stdClass && property_exists($decoded, 'data') && is_array($decoded->data)) {
        $rows = count($decoded->data);
    } else {
        nesti_fail("GET {$endpoint} returned neither a JSON array nor an object with an array \"data\"");
    }

    return ['rows' => $rows, 'queries' => $queries];
}

/** @param list<string> $queries */
function nesti_reads_table(array $queries, Connection $connection, string $table): bool
{
    $wrapped = $connection->getQueryGrammar()->wrapTable($table);
    $pattern = '/\b(?:from|join)\s+' . preg_quote($wrapped, '/') . '(?![A-Za-z0-9_])/i';
    foreach ($queries as $query) {
        if (preg_match('/^\s*select\b/i', $query) === 1 && preg_match($pattern, $query) === 1) {
            return true;
        }
    }

    return false;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

function nesti_main(): int
{
    $root = getcwd();
    if ($root === false || !is_file($root . '/artisan')) {
        nesti_fail('the working directory is not a Laravel application (no artisan)');
    }
    // A stale report must never describe this run.
    if (nesti_present(nesti_report_path())) {
        @unlink(nesti_report_path());
    }

    $requirements = nesti_load_requirements($root);
    nesti_say(count($requirements) . ' declared fixture(s) in ' . NESTI_MANIFEST_PATH);

    require $root . '/vendor/autoload.php';
    /** @var Application $app */
    $app = require $root . '/bootstrap/app.php';
    $console = $app->make(ConsoleKernel::class);
    $console->bootstrap();

    $database = realpath($root . '/database/database.sqlite');
    if ($database === false) {
        nesti_fail('database/database.sqlite does not exist');
    }
    nesti_assert_isolated($app->make('db')->connection(), $database, 'the default database connection');

    /** @var array<string, Model> $models */
    $models = [];
    foreach ($requirements as $requirement) {
        $class = $requirement['model'];
        $models[$class] ??= nesti_resolve_model($class, $root, $database);
    }

    nesti_say('migrate --force');
    $status = nesti_artisan($console, 'migrate', ['--force' => true]);
    if ($status !== 0) {
        nesti_fail("migrate exited with status {$status}");
    }

    /** @var array<string, string> $tables */
    $tables = [];
    foreach ($models as $class => $model) {
        $table = $model->getTable();
        if (strlen($table) > NESTI_MAX_NAME_CHARS || preg_match(NESTI_TABLE_RE, $table) !== 1) {
            nesti_fail("declared model {$class} uses the unsupported table identifier " . json_encode($table));
        }
        if (!$model->getConnection()->getSchemaBuilder()->hasTable($table)) {
            nesti_fail("declared model {$class}'s table {$table} does not exist after migration");
        }
        $tables[$class] = $table;
    }

    nesti_say('db:seed --force (default seeder)');
    $retained = null;
    try {
        $status = nesti_artisan($console, 'db:seed', ['--force' => true]);
        if ($status !== 0) {
            nesti_fail("default seeding exited with status {$status}");
        }
    } catch (NestiFixtureError $error) {
        throw $error;
    } catch (Throwable $error) {
        $seeder = nesti_unresolved_declared_seeder($error, $requirements, $root);
        if ($seeder === null) {
            throw $error;
        }
        $retained = ['seeder' => $seeder, 'message' => $error->getMessage()];
        nesti_say("default seeding stopped: {$error->getMessage()} (declared seeder; class and file absent)");
    }

    foreach ($requirements as $requirement) {
        ['endpoint' => $endpoint, 'model' => $class, 'seeder' => $seeder] = $requirement;
        $model = $models[$class];
        $table = $tables[$class];
        $connection = $model->getConnection();

        $probe = nesti_probe($app, $endpoint, $connection);
        if ($probe['rows'] > 0) {
            nesti_say("GET {$endpoint}: {$probe['rows']} row(s), fixture satisfied");
            continue;
        }
        if (!nesti_reads_table($probe['queries'], $connection, $table)) {
            nesti_fail("GET {$endpoint} returned no rows and ran no SELECT on table {$table}: "
                . "it cannot be confirmed to read {$class}");
        }
        if ($model->newQueryWithoutScopes()->exists()) {
            nesti_fail("GET {$endpoint} returned no rows although table {$table} has records: "
                . 'a contract/filtering failure, not missing fixture data');
        }
        nesti_say("GET {$endpoint}: no rows and table {$table} is empty");

        $file = nesti_seeder_file($root, $seeder);
        if (class_exists($seeder)) {
            if (!is_subclass_of($seeder, Seeder::class)) {
                nesti_fail("declared seeder {$seeder} is not an Illuminate\\Database\\Seeder");
            }
            if (!nesti_inside((new ReflectionClass($seeder))->getFileName(), realpath($root . '/database/seeders'))) {
                nesti_fail("declared seeder {$seeder} is not defined inside database/seeders");
            }
            nesti_say("db:seed --class={$seeder} --force");
            $status = nesti_artisan($console, 'db:seed', ['--class' => $seeder, '--force' => true]);
            if ($status !== 0) {
                nesti_fail("declared seeder {$seeder} exited with status {$status}");
            }
            $probe = nesti_probe($app, $endpoint, $connection);
            if ($probe['rows'] === 0) {
                nesti_fail("declared seeder {$seeder} ran, but GET {$endpoint} still returns no rows");
            }
            nesti_say("GET {$endpoint}: {$probe['rows']} row(s) after {$seeder}, fixture satisfied");
            continue;
        }
        if (nesti_present($file)) {
            nesti_fail("declared seeder {$seeder} cannot be loaded although "
                . substr($file, strlen($root) + 1) . ' exists: fix its class name, namespace or autoloading');
        }
        if ($retained !== null && $retained['seeder'] !== $seeder) {
            nesti_fail("default seeding failed: {$retained['message']}");
        }

        nesti_write_report([
            'version' => 1,
            'status' => 'missing_seeder',
            'requirement' => [
                'endpoint' => $endpoint,
                'model' => $class,
                'seeder' => $seeder,
                'table' => $table,
            ],
        ]);
        nesti_say("missing seeder: GET {$endpoint} needs {$seeder} (class and "
            . substr($file, strlen($root) + 1) . ' absent); browser tests not started');

        return NESTI_EXIT_MISSING_SEEDER;
    }

    if ($retained !== null) {
        nesti_fail("default seeding failed: {$retained['message']}");
    }
    nesti_write_report(['version' => 1, 'status' => 'ready']);
    nesti_say('ready');

    return NESTI_EXIT_READY;
}

try {
    $nestiExitCode = nesti_main();
} catch (NestiFixtureError $error) {
    fwrite(STDERR, "[nesti-fixtures] FAILED: {$error->getMessage()}\n");
    $nestiExitCode = NESTI_EXIT_FAILED;
} catch (Throwable $error) {
    fwrite(STDERR, sprintf(
        "[nesti-fixtures] FAILED: %s: %s (%s:%d)\n",
        get_class($error),
        $error->getMessage(),
        $error->getFile(),
        $error->getLine(),
    ));
    $nestiExitCode = NESTI_EXIT_FAILED;
}

exit($nestiExitCode);
