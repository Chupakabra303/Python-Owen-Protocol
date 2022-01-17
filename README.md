# Python-Owen-Protocol
Python 3.8.10 реализация протокола для приборов Овен.


За основу взят проект https://github.com/danilkorotkov/owenDoors, но глубоко переработан и переписан под Python 3.

Состав проекта:
- Owen.py - файл класса OwenProtocol, OwenDevice и вспомогательных классов.
- OwenExample1.py - базовый пример работы с классом OwenProtocol и OwenDevice
- OwenExample2.py - расширенный пример с Python GUI Tkinter
- OwenWithQueue.py - алтернативный файл класса OwenProtocol, OwenDevice и вспомогательных классов. Добавлена командная очередь.
- OwenWithQueueExample2.py - расширенный пример с Python GUI Tkinter с классом командной очереди

Рекомендуется использовать классы Owen.py без командной очереди. Командная очередь (OwenWithQueue.py) была введена для устранения проблем одновременного доступа к функциям класса для работы с последовательным портом. Но на данный момент в классах Owen.py для этого применяется мьютекс (mutex), который убрал эту проблему. 
