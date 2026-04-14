<?php
class Action {
    protected $path;
    protected $id;

    public function isPathValid()
    {  
        if(strpos($this->path, 'uploads') !== false) { 
            echo "Invalid path, access denied";
            exit();
        } 
        
        if ($this->id !== 0 && $this->id !== 1) {
            switch($this->id) {
                case 1:
                    if ($this->path) {
                        include($this->path);
                    }
                    break;
                case 0:
                    throw new Exception("id invalid in ".__CLASS__.__FUNCTION__);
                    break;
                default:
                    break;         
            }
        }
    }
}

class Content {

    public $formatters;

    public function format($formatter, $arguments = array())
    {
        return call_user_func_array($this->getFormatter($formatter), $arguments);
    }

    public function getFormatter($formatter)
    {
        if (isset($this->formatters[$formatter])) {
            return $this->formatters[$formatter];
        }
    
        foreach ($this->providers as $provider) {
            if (method_exists($provider, $formatter)) {
                $this->formatters[$formatter] = array($provider, $formatter);
                return $this->formatters[$formatter];
            }
        }
        throw new \InvalidArgumentException(sprintf('Unknown formatter "%s"', $formatter));
    }

    public function __call($method, $attributes)
    {
        return $this->format($method, $attributes);
    }
}

class Show{
    public $source;
    public $str;
    public $reader;
    public function __construct($file='index.php') {
        $this->source = $file;
        echo 'Welcome to '.$this->source."<br>";
    }
    public function __toString() {
        
        
        $this->str->reset();
    }

    public function __wakeup() {
        
        if(preg_match("/gopher|phar|http|file|ftp|dict|\.\./i", $this->source)) {
            throw new Exception('invalid protocol found in '.__CLASS__);
        }
    }

    public function reset() {
        if ($this->reader !== null) {
            
            
            $this->reader->close();
        }
    }
}


highlight_file(__FILE__);
