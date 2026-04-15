<?php
error_reporting(0);

require_once('config.php');
require_once('lib/util.php');
require_once('lib/session.php');

$session = new SecureClientSession(CLIENT_SESSION_ID, SECRET_KEY);
$filename = $_FILES['file']['name'];
$temp_name = $_FILES['file']['tmp_name'];
$size = $_FILES['file']['size'];
$error = $_FILES['file']['error'];
if ($size > 2*1024*1024){
    echo "<script>alert('文件过大');window.history.go(-1);</script>";
    exit();
}

$arr = pathinfo($filename);
$ext_suffix = $arr['extension'];
$allow_suffix = array('jpg','gif','jpeg','png');
if(!in_array($ext_suffix, $allow_suffix)){  
    echo "<script>alert('只能是jpg,gif,jpeg,png');window.history.go(-1);</script>";
    exit();
}

$new_filename = date('YmdHis',time()).rand(100,1000).'.'.$ext_suffix;
move_uploaded_file($temp_name, 'uploads/'.$new_filename);
flash('info', "success save in: ".'uploads/'.$new_filename);
$session->set('avatar', $filename);
redirect('/');

   



