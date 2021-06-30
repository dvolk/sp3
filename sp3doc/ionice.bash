sudo ionice -c Realtime -p $(ps ax | grep catweb | grep -v grep | awk '{ print $1 }')
sudo ionice -c Realtime -p $(ps ax | grep mongod | grep -v grep | awk '{ print $1 }')
sudo ionice -c Realtime -p $(ps ax | grep catreport/main.py | grep -v grep | awk '{ print $1 }')
