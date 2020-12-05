import torch
import torchvision
import torchvision.transforms as transforms
from torchvision import models
import torchvision
from PIL import Image
import torchvision.transforms as transforms
import torchvision.utils as vutils
from torch.utils.data import DataLoader
import torch.nn.init as init
net = models.wide_resnet50_2(pretrained=True)
test_transform=transforms.Compose([
                                transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),]
                              )
mnist_test_set = Image.open("A2.jpg")
  
    
classes = ( 'Bread',

'Dairy product',

'Dessert',

'Egg',

'Fried food',

'Meat',

'Noodles-Pasta',

'Rice',

'Seafood',

'Soup'

'Vegetable-Fruit'  )


val_loader= test_transform(mnist_test_set )


checkpoint = torch.load("best_mnist_checkpoint.pt")
net.load_state_dict(checkpoint['state_dict'])

outputs = net(val_loader[None, ...])
_, predicted = torch.max(outputs, 1)

print('Predicted: ', ' '.join('%5s' % classes[predicted[j]]
                              for j in range(1)))
prediction=' '.join('%5s' % classes[predicted[j]]
                              for j in range(1))
print(prediction)