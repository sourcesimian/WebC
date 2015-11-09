WebCompiler
===========
Assuming some sort of root directory (eg: example.com) the directory structure
should be as follows:

 -  example.com/<projectName>/
                              you can keep any project related files and
                              folders here, and also make backup copies of
                              your 'src' folder

 -  example.com/<projectName>/root/ - your site will compile to here

 -  example.com/<projectName>/src/ - build your web site in here
                                  style.html - A demonstration HTML file to show your current styles
                                  example.html - An empty template from which to begin new files
                                  _template.html - The main Jinja2 template file for your site
                                  ???.css - A Cascading Style Sheet for your site

 -  example.com/<projectName>/src/_watermark/
                                             watermark.cfg - Watermarker config file
                                             watermark.cfg.bak - Watermarker backp config file
                                             <Name>.gif - Watermark file
                                             <Name>.png - Watermark file
                                             Files beginning with  '_' wil be ignored

* Tools
========
  To run the tools open a Terminal, eg:
    Applications->Accessories->Terminal

  Then change directory into the root directory of your sites, eg:
    $ cd Documents/example.com/


  wc-compile
  -----------
    For further help on the tool:  $ ./wc-compile --help
    To run the compiler:           $ ./wc-compile <projectDir>
    where <projectDir> is the name of the sub-directory in which your site is stored.

    To run the compiler from a completely clean start, this will delete the entire 'root'
    directory first, i.e.: example.com/<projectName>/root
    Run this: $ ./wc-compile <projectDir> --clean

    To run the compiler to force re-generation of all generated files
    Run this: $ ./wc-compile <projectDir> --all

    And to run the compiler to force re-generation of all generated HTML files
    Run this: $ ./wc-compile <projectDir> --allHtml

    Basically the compiler copies all files from the 'src' directory to the 'root'
    directory. If it is a HTML file it is passed through the Jinja2 templater thus
    picking up any templating requirements. If the HTML file does not contain any,
    then it will simply be copied. If the file is an image (gif, jpg or png) it will
    be considered for water marking, if no instructions are found it will simply be
    copied. ANd finally any file with the name starting with a '_' will be ignored.

    If no extra switches i.e.: --clean, --all, --allHtml are specified the compiler
    will attempt to only compile the files where there will be resultant changes.
    It will however not notice all changes, for example when you change a Jinja2
    template (e.g.: _template.html). In this situation you will need to add the
    --allHtml switch. A quicker solution for reviewing the results of your changes,
    before processing all hte files is as follows:
        $ touch <projectDir>/src/style.html  &&  ./wc-compile <projectDir>
    this will cause this file '<projectDir>/src/style.html' to appear recently modified
    and so the compiler will process it and you can then view the output ion the
    'root' folder.


  wc-watermark
  ------------
    For further help on the tool:  $ ./wc-watermark --help
    To run the watermarker:        $ ./wc-watermark <projectDir>
    where <projectDir> is the name of the sub-directory in which your site is stored.

    Whilst running this tool the text output on the console can sometimes be useful
    to understanding it's operation.

    Each time you change a setting the tol will write a backup of the configuration
    to: example.com/<projectName>/src/_watermark/watermark.cfg.bak

  wc-analyse
  ----------
    For further help on the tool:  $ ./wc-analyse --help
                              or:  $ ./wc-analyse 
    To run the analyser:  $ ./wc-analyse <projectDir>
    where <projectDir> is the name of the sub-directory in which your site is stored.

    This tool will generate an analysis log and write it to your Current Working Directory
    i.e. the one that you are in e.g.: ../Documents/examples.com/

    The output will tell you the name of the file generated


  wc-process-logs
  ---------------
    For further help on the tool:  $ ./wc-process-logs --help
    To run the log processor, you need to be online with a link of reasonable quality
    then run:  $ ./wc-process-logs
    The script will require you to enter ONE password. This password will be used to
    access both the FTP and SMTP services configured in 'siteProcessLogs_config.py'.

    Once the script has successfully fetched log files and distributed them to the
    configured recipients. It will them amil a copy of the script, configuration and
    the history to the configured administrator.

    The complete log files will also be written to the current directory. The log format
    The Apache Log Format, there are many vey good applications available for analysing
    such logs further.


Resources
=========
There are some very good resources for learning an referencing HTML and CSS.
Googling for topics and including 'CSS' or 'HTML' can often return helpful
results:

The following sites are pretty good too:
- http://www.w3schools.com/
- http://www.gotapi.com/python


====


