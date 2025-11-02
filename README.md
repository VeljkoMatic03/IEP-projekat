IEP Projekat

This system is made of 4 separate flask microservices, each representing functionalities available to each user role, and already made to be easily deployable.

Auth service is used for registration and login of users, and uses a separate database compared to the rest of the system. Other three services are flask apps that 
use the same database (shop-db), and each have endpoints that represent functionalities that each role (owner, customer, courier) has. Each user has to be logged in 
(needs to have valid JWT token) to access any of these endpoints. SQLAlchemy ORM was used for database management.

I have also made one Solidity contract which encapsulates the whole ordering, delivering and payment proccess. Since this is a university project, owner's private key 
is already predetermined since the Ganache is configured with mnemonic. 

There are dockerfiles for each microservice, as well as yaml file which can be used to compose the whole system.

Project was tested by public tests made by TA. Payment by customer was not realized and was done by those tests.
