<?php

/** Render and record official Boost 2.10.3 artifacts in an offline scratch app. */
declare(strict_types=1);

use Composer\InstalledVersions;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Foundation\Bootstrap\LoadConfiguration;
use Laravel\Boost\Contracts\SupportsSkills;
use Laravel\Boost\Install\GuidelineAssist;
use Laravel\Boost\Install\GuidelineConfig;
use Laravel\Boost\Install\Skill;
use Laravel\Boost\Install\SkillWriter;
use Laravel\Boost\Rules\RuleRepository;
use Laravel\Boost\Support\RenderFailures;
use Laravel\Roster\ProjectManager;

try {
    $operation = $argv[1] ?? '';
    if (! in_array($operation, ['prepare', 'record'], true)) {
        throw new RuntimeException('Expected prepare or record operation.');
    }
    $root = getcwd();
    $scratch = $root.'/.nesti-boost';
    if (! is_dir($scratch) && ! mkdir($scratch, 0700, true)) {
        throw new RuntimeException('Cannot create scratch result directory.');
    }
    foreach ([
        'APP_ENV' => 'testing', 'APP_DEBUG' => 'false',
        'APP_KEY' => 'base64:'.base64_encode(random_bytes(32)),
        'DB_CONNECTION' => 'sqlite', 'DB_DATABASE' => ':memory:',
        'DB_URL' => '', 'DATABASE_URL' => '',
        'CACHE_STORE' => 'array', 'CACHE_DRIVER' => 'array',
        'SESSION_DRIVER' => 'array', 'QUEUE_CONNECTION' => 'sync',
        'MAIL_MAILER' => 'log', 'LOG_CHANNEL' => 'stderr',
        'BOOST_ENABLED' => 'false', 'TELESCOPE_ENABLED' => 'false',
    ] as $name => $value) {
        putenv($name.'='.$value);
        $_ENV[$name] = $value;
        $_SERVER[$name] = $value;
    }
    foreach (['bootstrap/cache', 'storage/framework/views', 'storage/framework/cache', 'storage/framework/sessions', 'storage/logs'] as $directory) {
        if (! is_dir($root.'/'.$directory) && ! mkdir($root.'/'.$directory, 0700, true)) {
            throw new RuntimeException('Cannot prepare scratch runtime directory: '.$directory);
        }
    }
    require $root.'/vendor/autoload.php';
    if (ltrim((string) InstalledVersions::getPrettyVersion('laravel/boost'), 'v') !== '2.10.3') {
        throw new RuntimeException('Official laravel/boost 2.10.3 is required.');
    }
    $app = require $root.'/bootstrap/app.php';
    $app->afterBootstrapping(LoadConfiguration::class, function ($app): void {
        $config = $app->make('config');
        $connections = [];
        foreach (array_keys($config->get('database.connections', [])) as $name) {
            $connections[$name] = ['driver' => 'sqlite', 'database' => ':memory:', 'prefix' => ''];
        }
        $connections['sqlite'] = ['driver' => 'sqlite', 'database' => ':memory:', 'prefix' => ''];
        $config->set([
            'app.env' => 'testing', 'app.debug' => false,
            'database.default' => 'sqlite', 'database.connections' => $connections,
            'cache.default' => 'array', 'cache.stores' => ['array' => ['driver' => 'array']],
            'session.driver' => 'array', 'queue.default' => 'sync',
            'mail.default' => 'log', 'mail.mailers' => ['log' => ['transport' => 'log']],
            'logging.default' => 'stderr', 'boost.enabled' => false,
        ]);
    });
    $app->make(Kernel::class)->bootstrap();
    // Boost disables its normal integration while testing; bind only renderer dependencies.
    $app->singleton(RenderFailures::class, fn (): RenderFailures => new RenderFailures);
    $app->singleton(GuidelineAssist::class, fn (): GuidelineAssist => new GuidelineAssist(
        new ProjectManager, new GuidelineConfig
    ));

    if ($operation === 'prepare') {
        $agent = new class implements SupportsSkills {
            public function skillsPath(): string
            {
                return '.ai/nesti-boost-skills';
            }
        };
        $skill = new Skill(
            name: 'infer-conventions', package: 'laravel/boost',
            path: base_path('vendor/laravel/boost/.ai/boost/skill/infer-conventions'),
            description: 'Official pinned convention discovery workflow',
        );
        $result = (new SkillWriter($agent))->write($skill);
        $failures = $app->make(RenderFailures::class);
        if (! in_array($result, [SkillWriter::SUCCESS, SkillWriter::UPDATED], true) || ! $failures->isEmpty()) {
            throw new RuntimeException('Boost rendering failed: '.implode(', ', $failures->paths()));
        }
        $rendered = [];
        foreach (['skill' => 'SKILL.md', 'checklist' => 'references/checklist.md'] as $key => $file) {
            $content = file_get_contents(base_path($agent->skillsPath().'/infer-conventions/'.$file));
            if ($content === false || trim($content) === '' || preg_match('/@(?:if|endif|php|endphp)\b|\$assist->/', $content)) {
                throw new RuntimeException('Empty or unrendered official Boost content: '.$file);
            }
            $rendered[$key] = $content;
        }
        $packages = [];
        foreach (InstalledVersions::getInstalledPackages() as $package) {
            $packages[$package] = InstalledVersions::getPrettyVersion($package);
        }
        ksort($packages);
        $payload = ['package_version' => '2.10.3', ...$rendered, 'packages' => $packages];
    } else {
        $entries = json_decode(file_get_contents($scratch.'/record-input.json'), true, 512, JSON_THROW_ON_ERROR);
        if (! is_array($entries) || ! array_is_list($entries)) {
            throw new RuntimeException('Expected a validated rule list.');
        }
        $repository = new RuleRepository(base_path('.ai/rules'));
        $records = [];
        foreach ($entries as $entry) {
            foreach (['id', 'glob', 'title', 'note'] as $key) {
                if (! isset($entry[$key]) || ! is_string($entry[$key]) || trim($entry[$key]) === '') {
                    throw new RuntimeException('Invalid rule '.$key);
                }
            }
            if (str_starts_with($entry['glob'], '/') || str_contains($entry['glob'], '..') || str_contains($entry['glob'], '\\')) {
                throw new RuntimeException('Rule glob must be relative.');
            }
            $path = $repository->write($entry['glob'], $entry['title'], $entry['note']);
            $records[] = ['id' => $entry['id'], 'source_rule' => $repository->relativePath($path)];
        }
        foreach ($records as &$record) {
            $record['content'] = file_get_contents(base_path($record['source_rule']));
            if ($record['content'] === false || trim($record['content']) === '') {
                throw new RuntimeException('Official Boost rule was not written.');
            }
        }
        unset($record);
        $payload = ['package_version' => '2.10.3', 'records' => $records];
    }
    $json = json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
    if (file_put_contents($scratch.'/'.$operation.'.json', $json) === false) {
        throw new RuntimeException('Unable to write Boost result.');
    }
    chmod($scratch.'/'.$operation.'.json', 0600);
} catch (Throwable $error) {
    fwrite(STDERR, 'Nesti Boost prerequisite failed: '.$error->getMessage().PHP_EOL);
    exit(1);
}
