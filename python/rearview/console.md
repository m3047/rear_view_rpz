<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html><head><title>Python: module rearview.console</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
</head><body bgcolor="#f0f0f8">

<table width="100%" cellspacing=0 cellpadding=2 border=0 summary="heading">
<tr bgcolor="#7799ee">
<td valign=bottom>&nbsp;<br>
<font color="#ffffff" face="helvetica, arial">&nbsp;<br><big><big><strong><a href="rearview.html"><font color="#ffffff">rearview</font></a>.console</strong></big></big></font></td
><td align=right valign=bottom
><font color="#ffffff" face="helvetica, arial"><a href=".">index</a><br><a href="file:/home/m3047/GitHub/rear_view_rpz/python/rearview/console.py">/home/m3047/GitHub/rear_view_rpz/python/rearview/console.py</a></font></td></tr></table>
    <p><tt>An&nbsp;interactive&nbsp;console.<br>
&nbsp;<br>
This&nbsp;console&nbsp;is&nbsp;enabled&nbsp;by&nbsp;setting&nbsp;for&nbsp;example<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;CONSOLE&nbsp;=&nbsp;{&nbsp;'host':'127.0.0.1',&nbsp;'port':3047&nbsp;}<br>
&nbsp;<br>
in&nbsp;the&nbsp;configuration&nbsp;file.<br>
&nbsp;<br>
The&nbsp;purpose&nbsp;of&nbsp;the&nbsp;console&nbsp;is&nbsp;to&nbsp;allow&nbsp;interactive&nbsp;examination&nbsp;of&nbsp;in-memory<br>
data&nbsp;structures&nbsp;and&nbsp;caches.<br>
&nbsp;<br>
The&nbsp;commands&nbsp;are&nbsp;synchronous&nbsp;with&nbsp;respect&nbsp;to&nbsp;the&nbsp;operation&nbsp;of&nbsp;the&nbsp;server,&nbsp;which<br>
is&nbsp;to&nbsp;say&nbsp;the&nbsp;server&nbsp;isn't&nbsp;doing&nbsp;anything&nbsp;else&nbsp;until&nbsp;the&nbsp;underlying&nbsp;operation<br>
has&nbsp;completed.&nbsp;This&nbsp;provides&nbsp;a&nbsp;better&nbsp;snapshot&nbsp;of&nbsp;the&nbsp;state&nbsp;at&nbsp;any&nbsp;given&nbsp;moment,<br>
but&nbsp;can&nbsp;negatively&nbsp;impact&nbsp;data&nbsp;collection&nbsp;from&nbsp;a&nbsp;busy&nbsp;server.<br>
&nbsp;<br>
IPv6&nbsp;addresses&nbsp;are&nbsp;expected&nbsp;to&nbsp;be&nbsp;in&nbsp;the&nbsp;compressed&nbsp;rather&nbsp;than&nbsp;expanded&nbsp;format.<br>
&nbsp;<br>
The&nbsp;following&nbsp;commands&nbsp;are&nbsp;supported:<br>
&nbsp;<br>
Address&nbsp;to&nbsp;zone&nbsp;correlation<br>
---------------------------<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;a2z<br>
&nbsp;&nbsp;&nbsp;&nbsp;<br>
Perform&nbsp;a&nbsp;crosscheck&nbsp;of&nbsp;the&nbsp;addresses&nbsp;in&nbsp;db.RearView.associations&nbsp;and<br>
rpz.RPZ.contents.&nbsp;Technically&nbsp;the&nbsp;former&nbsp;are&nbsp;addresses&nbsp;(1.2.3.4),&nbsp;while&nbsp;the<br>
latter&nbsp;are&nbsp;PTR&nbsp;FQDNs&nbsp;(4.3.2.1.in-addr.arpa).<br>
&nbsp;<br>
Address&nbsp;details<br>
---------------<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;addr{ess}&nbsp;&lt;some-address&gt;<br>
&nbsp;&nbsp;&nbsp;&nbsp;<br>
Get&nbsp;details&nbsp;regarding&nbsp;an&nbsp;address'&nbsp;resolutions&nbsp;and&nbsp;best&nbsp;resolution,&nbsp;and<br>
whether&nbsp;this&nbsp;is&nbsp;reflected&nbsp;in&nbsp;the&nbsp;zone&nbsp;construct.<br>
&nbsp;<br>
Zone&nbsp;details<br>
------------<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;entry&nbsp;&lt;some-address&gt;<br>
&nbsp;<br>
Compares&nbsp;what&nbsp;is&nbsp;in&nbsp;the&nbsp;in-memory&nbsp;zone&nbsp;view&nbsp;to&nbsp;what&nbsp;is&nbsp;actually&nbsp;present&nbsp;in<br>
the&nbsp;zone-as-served.&nbsp;NOTE&nbsp;THAT&nbsp;THE&nbsp;ACTUAL&nbsp;DNS&nbsp;REQUEST&nbsp;IS&nbsp;SYNCHRONOUS.&nbsp;This<br>
command&nbsp;causes&nbsp;a&nbsp;separate&nbsp;DNS&nbsp;request&nbsp;to&nbsp;be&nbsp;issued&nbsp;outside&nbsp;of&nbsp;the&nbsp;TCP<br>
connection,&nbsp;which&nbsp;negatively&nbsp;impacts&nbsp;performance&nbsp;of&nbsp;the&nbsp;agent.<br>
&nbsp;<br>
Queue&nbsp;depth<br>
-----------<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;qd<br>
&nbsp;&nbsp;&nbsp;&nbsp;<br>
The&nbsp;depths&nbsp;of&nbsp;various&nbsp;processing&nbsp;queues.<br>
&nbsp;<br>
Cache&nbsp;eviction&nbsp;queue<br>
--------------------<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;cache&nbsp;[&lt;|&gt;]&nbsp;&lt;number&gt;<br>
&nbsp;<br>
Display&nbsp;information&nbsp;about&nbsp;the&nbsp;entries&nbsp;(addresses)&nbsp;at&nbsp;the&nbsp;beginning&nbsp;(&lt;)<br>
or&nbsp;end&nbsp;(&gt;)&nbsp;of&nbsp;the&nbsp;queue.&nbsp;The&nbsp;specified&nbsp;number&nbsp;of&nbsp;entries&nbsp;is&nbsp;displayed.<br>
&nbsp;<br>
Cache&nbsp;Evictions<br>
---------------<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;evict{ions}&nbsp;&lt;number&gt;<br>
&nbsp;&nbsp;&nbsp;&nbsp;<br>
Displays&nbsp;a&nbsp;logic&nbsp;readout&nbsp;of&nbsp;the&nbsp;most&nbsp;recent&nbsp;"n"&nbsp;cache&nbsp;evictions.&nbsp;There&nbsp;is<br>
an&nbsp;internal&nbsp;limit&nbsp;on&nbsp;the&nbsp;number&nbsp;of&nbsp;evictions&nbsp;which&nbsp;are&nbsp;retained&nbsp;for<br>
review.<br>
&nbsp;<br>
Zone&nbsp;Data&nbsp;Refresh<br>
-----------------<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;refr{esh}&nbsp;&lt;number&gt;<br>
&nbsp;<br>
Displays&nbsp;a&nbsp;logic&nbsp;readout&nbsp;of&nbsp;the&nbsp;most&nbsp;recent&nbsp;"n"&nbsp;zone&nbsp;refresh&nbsp;batches.&nbsp;Resolutions<br>
which&nbsp;survive&nbsp;"sheep&nbsp;shearing"&nbsp;(cache&nbsp;eviction)&nbsp;are&nbsp;scheduled&nbsp;for&nbsp;having&nbsp;updated<br>
information&nbsp;written&nbsp;back&nbsp;to&nbsp;the&nbsp;zone&nbsp;file&nbsp;in&nbsp;batches&nbsp;to&nbsp;minimize&nbsp;performance&nbsp;impacts;<br>
if&nbsp;things&nbsp;are&nbsp;really&nbsp;busy&nbsp;everything&nbsp;may&nbsp;not&nbsp;get&nbsp;refreshed.<br>
&nbsp;<br>
Batches&nbsp;go&nbsp;through&nbsp;three&nbsp;phases,&nbsp;at&nbsp;least&nbsp;for&nbsp;logging&nbsp;purposes:<br>
&nbsp;<br>
1)&nbsp;The&nbsp;batch&nbsp;is&nbsp;created.<br>
2)&nbsp;The&nbsp;batch&nbsp;is&nbsp;accumulating&nbsp;addresses&nbsp;to&nbsp;update&nbsp;with&nbsp;fresh&nbsp;information.<br>
3)&nbsp;The&nbsp;batch&nbsp;is&nbsp;written&nbsp;to&nbsp;the&nbsp;zone&nbsp;as&nbsp;an&nbsp;update.<br>
&nbsp;<br>
Quit<br>
----<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;quit<br>
&nbsp;&nbsp;&nbsp;&nbsp;<br>
Ends&nbsp;the&nbsp;console&nbsp;session;&nbsp;no&nbsp;other&nbsp;response&nbsp;occurs.<br>
&nbsp;<br>
Response&nbsp;Codes<br>
--------------<br>
&nbsp;<br>
Each&nbsp;response&nbsp;line&nbsp;is&nbsp;prepended&nbsp;by&nbsp;one&nbsp;of&nbsp;these&nbsp;codes&nbsp;and&nbsp;an&nbsp;ASCII&nbsp;space.<br>
&nbsp;<br>
&nbsp;&nbsp;&nbsp;&nbsp;200&nbsp;Success,&nbsp;single&nbsp;line&nbsp;output.<br>
&nbsp;&nbsp;&nbsp;&nbsp;210&nbsp;Success,&nbsp;beginning&nbsp;of&nbsp;multi-line&nbsp;output.<br>
&nbsp;&nbsp;&nbsp;&nbsp;212&nbsp;Success,&nbsp;continuation&nbsp;line.<br>
&nbsp;&nbsp;&nbsp;&nbsp;400&nbsp;User&nbsp;error&nbsp;/&nbsp;bad&nbsp;request.<br>
&nbsp;&nbsp;&nbsp;&nbsp;500&nbsp;Not&nbsp;found&nbsp;or&nbsp;internal&nbsp;error.</tt></p>
<p>
<table width="100%" cellspacing=0 cellpadding=2 border=0 summary="section">
<tr bgcolor="#aa55cc">
<td colspan=3 valign=bottom>&nbsp;<br>
<font color="#ffffff" face="helvetica, arial"><big><strong>Modules</strong></big></font></td></tr>
    
<tr><td bgcolor="#aa55cc"><tt>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</tt></td><td>&nbsp;</td>
<td width="100%"><table width="100%" summary="list"><tr><td width="25%" valign=top><a href="asyncio.html">asyncio</a><br>
</td><td width="25%" valign=top><a href="logging.html">logging</a><br>
</td><td width="25%" valign=top><a href="time.html">time</a><br>
</td><td width="25%" valign=top></td></tr></table></td></tr></table><p>
<table width="100%" cellspacing=0 cellpadding=2 border=0 summary="section">
<tr bgcolor="#ee77aa">
<td colspan=3 valign=bottom>&nbsp;<br>
<font color="#ffffff" face="helvetica, arial"><big><strong>Classes</strong></big></font></td></tr>
    
<tr><td bgcolor="#ee77aa"><tt>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</tt></td><td>&nbsp;</td>
<td width="100%"><dl>
<dt><font face="helvetica, arial"><a href="builtins.html#object">builtins.object</a>
</font></dt><dd>
<dl>
<dt><font face="helvetica, arial"><a href="rearview.console.html#Context">Context</a>
</font></dt><dt><font face="helvetica, arial"><a href="rearview.console.html#Request">Request</a>
</font></dt></dl>
</dd>
</dl>
 <p>
<table width="100%" cellspacing=0 cellpadding=2 border=0 summary="section">
<tr bgcolor="#ffc8d8">
<td colspan=3 valign=bottom>&nbsp;<br>
<font color="#000000" face="helvetica, arial"><a name="Context">class <strong>Context</strong></a>(<a href="builtins.html#object">builtins.object</a>)</font></td></tr>
    
<tr bgcolor="#ffc8d8"><td rowspan=2><tt>&nbsp;&nbsp;&nbsp;</tt></td>
<td colspan=2><tt><a href="#Context">Context</a>&nbsp;for&nbsp;the&nbsp;console.<br>&nbsp;</tt></td></tr>
<tr><td>&nbsp;</td>
<td width="100%">Methods defined here:<br>
<dl><dt><a name="Context-__init__"><strong>__init__</strong></a>(self, dnstap=None)</dt><dd><tt>Create&nbsp;a&nbsp;context&nbsp;<a href="builtins.html#object">object</a>.<br>
&nbsp;<br>
dnstap&nbsp;is&nbsp;normally&nbsp;set&nbsp;in&nbsp;code,&nbsp;but&nbsp;we&nbsp;pass&nbsp;it&nbsp;in&nbsp;with&nbsp;a&nbsp;default&nbsp;of<br>
None&nbsp;to&nbsp;make&nbsp;its&nbsp;presence&nbsp;known.</tt></dd></dl>

<dl><dt><a name="Context-handle_requests"><strong>handle_requests</strong></a>(self, reader, writer)</dt></dl>

<hr>
Data descriptors defined here:<br>
<dl><dt><strong>__dict__</strong></dt>
<dd><tt>dictionary&nbsp;for&nbsp;instance&nbsp;variables&nbsp;(if&nbsp;defined)</tt></dd>
</dl>
<dl><dt><strong>__weakref__</strong></dt>
<dd><tt>list&nbsp;of&nbsp;weak&nbsp;references&nbsp;to&nbsp;the&nbsp;object&nbsp;(if&nbsp;defined)</tt></dd>
</dl>
</td></tr></table> <p>
<table width="100%" cellspacing=0 cellpadding=2 border=0 summary="section">
<tr bgcolor="#ffc8d8">
<td colspan=3 valign=bottom>&nbsp;<br>
<font color="#000000" face="helvetica, arial"><a name="Request">class <strong>Request</strong></a>(<a href="builtins.html#object">builtins.object</a>)</font></td></tr>
    
<tr bgcolor="#ffc8d8"><td rowspan=2><tt>&nbsp;&nbsp;&nbsp;</tt></td>
<td colspan=2><tt>Everything&nbsp;to&nbsp;do&nbsp;with&nbsp;processing&nbsp;a&nbsp;request.<br>
&nbsp;<br>
The&nbsp;idiom&nbsp;is&nbsp;generally&nbsp;<a href="#Request">Request</a>(message).response&nbsp;and&nbsp;then&nbsp;do&nbsp;whatever&nbsp;is&nbsp;sensible<br>
with&nbsp;response.&nbsp;Response&nbsp;can&nbsp;be&nbsp;nothing,&nbsp;in&nbsp;which&nbsp;case&nbsp;there&nbsp;is&nbsp;nothing&nbsp;further<br>
to&nbsp;do.<br>&nbsp;</tt></td></tr>
<tr><td>&nbsp;</td>
<td width="100%">Methods defined here:<br>
<dl><dt><a name="Request-__init__"><strong>__init__</strong></a>(self, message, dnstap)</dt><dd><tt>Initialize&nbsp;self.&nbsp;&nbsp;See&nbsp;help(type(self))&nbsp;for&nbsp;accurate&nbsp;signature.</tt></dd></dl>

<dl><dt><a name="Request-a2z"><strong>a2z</strong></a>(self, request)</dt><dd><tt>a2z</tt></dd></dl>

<dl><dt><a name="Request-address"><strong>address</strong></a>(self, request)</dt><dd><tt>addr{ess}&nbsp;&lt;some-address&gt;<br>
&nbsp;<br>
Kind&nbsp;of&nbsp;a&nbsp;hot&nbsp;mess,&nbsp;but&nbsp;here's&nbsp;what's&nbsp;going&nbsp;on:<br>
&nbsp;<br>
*&nbsp;If&nbsp;there's&nbsp;no&nbsp;best&nbsp;resolution&nbsp;it&nbsp;could&nbsp;be&nbsp;that's&nbsp;because&nbsp;it&nbsp;was&nbsp;loaded<br>
&nbsp;&nbsp;from&nbsp;the&nbsp;actual&nbsp;zone&nbsp;file,&nbsp;which&nbsp;we&nbsp;can&nbsp;tell&nbsp;if&nbsp;it&nbsp;has&nbsp;a&nbsp;depth&nbsp;&gt;&nbsp;1&nbsp;and<br>
&nbsp;&nbsp;the&nbsp;first&nbsp;entry&nbsp;is&nbsp;None.<br>
&nbsp;&nbsp;<br>
*&nbsp;Other&nbsp;things.</tt></dd></dl>

<dl><dt><a name="Request-bad_request"><strong>bad_request</strong></a>(self, reason)</dt><dd><tt>A&nbsp;bad/unrecognized&nbsp;request.</tt></dd></dl>

<dl><dt><a name="Request-cache"><strong>cache</strong></a>(self, request)</dt><dd><tt>cache&nbsp;[&lt;|&gt;]&nbsp;&lt;number&gt;</tt></dd></dl>

<dl><dt><a name="Request-dispatch_request"><strong>dispatch_request</strong></a>(self, request)</dt><dd><tt>Called&nbsp;by&nbsp;<a href="#Request-__init__">__init__</a>()&nbsp;to&nbsp;dispatch&nbsp;the&nbsp;request.</tt></dd></dl>

<dl><dt><a name="Request-entry"><strong>entry</strong></a>(self, request)</dt><dd><tt>entry&nbsp;&lt;some-address&gt;</tt></dd></dl>

<dl><dt><a name="Request-evictions"><strong>evictions</strong></a>(self, request)</dt><dd><tt>evictions&nbsp;&lt;number&gt;</tt></dd></dl>

<dl><dt><a name="Request-qd"><strong>qd</strong></a>(self, request)</dt><dd><tt>qd</tt></dd></dl>

<dl><dt><a name="Request-quit"><strong>quit</strong></a>(self, request)</dt><dd><tt>quit</tt></dd></dl>

<dl><dt><a name="Request-refresh"><strong>refresh</strong></a>(self, request)</dt><dd><tt>refresh&nbsp;&lt;number&gt;</tt></dd></dl>

<dl><dt><a name="Request-validate_request"><strong>validate_request</strong></a>(self, request)</dt></dl>

<hr>
Data descriptors defined here:<br>
<dl><dt><strong>__dict__</strong></dt>
<dd><tt>dictionary&nbsp;for&nbsp;instance&nbsp;variables&nbsp;(if&nbsp;defined)</tt></dd>
</dl>
<dl><dt><strong>__weakref__</strong></dt>
<dd><tt>list&nbsp;of&nbsp;weak&nbsp;references&nbsp;to&nbsp;the&nbsp;object&nbsp;(if&nbsp;defined)</tt></dd>
</dl>
<hr>
Data and other attributes defined here:<br>
<dl><dt><strong>ABBREVIATED</strong> = {'address', 'cache', 'entry', 'evictions', 'refresh'}</dl>

<dl><dt><strong>COMMANDS</strong> = {'a2z': 1, 'address': 2, 'cache': 3, 'entry': 2, 'evictions': 2, 'qd': 1, 'quit': 1, 'refresh': 2}</dl>

</td></tr></table></td></tr></table>
</body></html>