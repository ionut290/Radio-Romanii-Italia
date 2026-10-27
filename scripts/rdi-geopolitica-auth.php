<?php
declare(strict_types=1);
// A one-time, locally executed AzuraCast API token helper.
// Never prints accounts, private keys, passwords or access tokens in probe mode.
require '/var/azuracast/www/vendor/autoload.php';
$env = \App\AppFactory::buildEnvironment();
$di = \App\AppFactory::buildContainer(\App\AppFactory::createContainerBuilder($env));
$em = $di->get(\Doctrine\ORM\EntityManagerInterface::class);
$mode = $argv[1] ?? 'probe';
if ($mode === 'probe') {
    $users = $em->getRepository(\App\Entity\User::class)->findAll();
    $admin = 0;
    foreach ($users as $user) {
        foreach ($user->roles as $role) {
            if (stripos($role->name, 'admin') !== false) {
                $admin++;
                break;
            }
        }
    }
    $station = $em->getRepository(\App\Entity\Station::class)->findOneBy(['short_name'=>'radio-romanii-italia']);
    $playlists = $station ? $em->getRepository(\App\Entity\StationPlaylist::class)->findBy(['station'=>$station]) : [];
    echo 'AZURA_ORM=ok' . PHP_EOL;
    echo 'AZURA_ADMIN_ACCOUNTS=' . $admin . PHP_EOL;
    echo 'AZURA_STATION=' . ($station ? 'found' : 'missing') . PHP_EOL;
    foreach ($playlists as $playlist) {
        echo 'PLAYLIST=' . $playlist->id . '|' . $playlist->name . '|' . $playlist->type->value . '|' . ($playlist->is_enabled?'enabled':'disabled') . PHP_EOL;
    }
    exit(0);
}
if ($mode === 'create') {
    // A temporary scoped-by-user API key that is revoked by the deploy script.
    $users = $em->getRepository(\App\Entity\User::class)->findAll();
    $admin = null;
    foreach ($users as $user) {
        foreach ($user->roles as $role) {
            if (stripos($role->name, 'admin') !== false) {
                $admin = $user;
                break 2;
            }
        }
    }
    if (!$admin) {
        fwrite(STDERR, 'Administrator AzuraCast unavailable' . PHP_EOL);
        exit(2);
    }
    $token = \App\Security\SplitToken::generate();
    $record = new \App\Entity\ApiKey($admin, $token, 'RDI Geopolitica - temporary hourly integration');
    $em->persist($record);
    $em->flush();
    // Token is captured by root's subprocess stdout; NEVER print in CI logs.
    echo (string)$token;
    exit(0);
}
if ($mode === 'revoke') {
    $id = $argv[2] ?? '';
    if (!preg_match('/^[a-f0-9]{16}$/', $id)) {
        fwrite(STDERR, 'Invalid key identifier' . PHP_EOL);
        exit(2);
    }
    $record = $em->getRepository(\App\Entity\ApiKey::class)->find($id);
    if ($record && $record->comment === 'RDI Geopolitica - temporary hourly integration') {
        $em->remove($record);
        $em->flush();
        echo 'Temporary AzuraCast key revoked.' . PHP_EOL;
    }
    exit(0);
}
fwrite(STDERR, 'Unsupported helper mode' . PHP_EOL);
exit(2);
