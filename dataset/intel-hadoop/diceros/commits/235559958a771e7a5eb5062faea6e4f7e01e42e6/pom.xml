project-diceros
===============

Diceros is a sub-project of Rhino project which focus on providing a hardware accelerated JCE provider. Initial effort include:
* AES-NI enabled AES/CTR/NOPADDING encryption/decryption support
* Hardware based true random generator (DRNG)

Diceros is not a full featured JCE provider yet for now, but we will make continuous effort towards that goal. You can download the source code and follow the instruction to build it, we have test the functionality in OpenJDK 7.

### Quick Start

https://github.com/intel-hadoop/diceros/wiki/Quick-Start

### Prerequisite
#### Hardware prerequisite:   
* Intel® Digital Random Number Generator (DRNG)   
* AES-NI

#### Software prerequisite:   
* <p>openssl-1.0.1c or above(just test openssl-1.0.1e);  </p> 
* <p>yasm-1.2.0 </p>
* <p>openjdk7;    </p>
* <p>add "libdiceros.so" and "libaesmb.so" (which are generated after build) to the environment variable "java.library.path"; </p>
* <p>add "diceros-1.0.0.jar"(which is generated after build) to the classpath; </p>

### Build 
mvn package

### Validate
mvn test  

### Deploy
#### Static deploy:   
add line "security.provider.10=com.intel.diceros.provider.DicerosProvider" in file "\<java-home\>\lib\security\java.security"

#### Dynamic deploy:   
add the following line "Security.addProvider(new com.intel.diceros.provider.DicerosProvider());"    
before calling method "SecureRandom.getInstace()" or "Cipher.getInstance()".

### Troubleshooting
https://github.com/intel-hadoop/diceros/wiki/Troubleshooting
