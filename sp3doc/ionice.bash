sudo ionice -c Realtime -p $(ps ax | grep catweb/ui | grep -v grep | awk '{ print $1 }')
sudo ionice -c Realtime -p $(ps ax | grep catweb/api | grep -v grep | awk '{ print $1 }')
sudo ionice -c Realtime -p $(ps ax | grep catreport/catreportreader.py | grep -v grep | awk '{ print $1 }')
sudo ionice -c Realtime -p $(ps ax | grep catreport/main.py | grep -v grep | awk '{ print $1 }')
