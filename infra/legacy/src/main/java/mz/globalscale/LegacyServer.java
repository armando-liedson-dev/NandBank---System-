package mz.globalscale;

import com.sun.net.httpserver.HttpsConfigurator;
import com.sun.net.httpserver.HttpsParameters;
import com.sun.net.httpserver.HttpsServer;
import com.sun.net.httpserver.HttpExchange;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import javax.net.ssl.*;
import java.io.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.regex.*;

/** Simulador de sistema legado, Java 21, JSON contratual, HTTPS com certificado de cliente e HMAC. */
public final class LegacyServer {
    private static final byte[] SECRET=System.getenv("INTEGRITY_KEY").getBytes(StandardCharsets.UTF_8);

    private static SSLContext context()throws Exception {
        String password=System.getenv("CERT_PASSWORD");
        KeyStore identity=KeyStore.getInstance("PKCS12");
        try(InputStream in=Files.newInputStream(Path.of("/certs/legacy.p12"))){identity.load(in,password.toCharArray());}
        KeyManagerFactory kmf=KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        kmf.init(identity,password.toCharArray());
        KeyStore trust=KeyStore.getInstance("PKCS12");
        try(InputStream in=Files.newInputStream(Path.of("/tmp/truststore.p12"))){trust.load(in,password.toCharArray());}
        TrustManagerFactory tmf=TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        tmf.init(trust);
        SSLContext ctx=SSLContext.getInstance("TLSv1.3");ctx.init(kmf.getKeyManagers(),tmf.getTrustManagers(),new SecureRandom());return ctx;
    }
    private static String hex(byte[] b){
        char[] out=new char[b.length*2];final char[] h="0123456789abcdef".toCharArray();
        for(int i=0;i<b.length;i++){out[i*2]=h[(b[i]>>>4)&15];out[i*2+1]=h[b[i]&15];}return new String(out);
    }
    private static String hmac(byte[] raw)throws Exception {
        Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(SECRET,"HmacSHA256"));return hex(mac.doFinal(raw));
    }
    private static String stringField(String data,String key){
        Matcher m=Pattern.compile("\\\""+Pattern.quote(key)+"\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"").matcher(data);
        return m.find()?m.group(1):"";
    }
    private static long amountField(String data){
        Matcher m=Pattern.compile("\\\"amount_minor\\\"\\s*:\\s*(\\d+)").matcher(data);
        return m.find()?Long.parseLong(m.group(1)):-1;
    }
    private static void reply(HttpExchange ex,int code,String json)throws IOException {
        byte[] bytes=json.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type","application/json; charset=utf-8");
        ex.sendResponseHeaders(code,bytes.length);
        try(OutputStream out=ex.getResponseBody()){out.write(bytes);}
    }
    public static void main(String[] args)throws Exception {
        SSLContext ssl=context();
        HttpsServer server=HttpsServer.create(new InetSocketAddress("0.0.0.0",8090),0);
        server.setHttpsConfigurator(new HttpsConfigurator(ssl){
            @Override public void configure(HttpsParameters p){
                SSLParameters params=getSSLContext().getDefaultSSLParameters();
                params.setNeedClientAuth(true);p.setSSLParameters(params);
            }
        });
        server.createContext("/legacy/validate",exchange->{
            if(!exchange.getRequestMethod().equals("POST")){reply(exchange,405,"{\"approved\":false,\"error\":\"METHOD\"}");return;}
            byte[] bytes=exchange.getRequestBody().readAllBytes();
            try{
                String provided=exchange.getRequestHeaders().getFirst("X-Integrity-HMAC");
                if(provided==null||!MessageDigest.isEqual(provided.getBytes(StandardCharsets.UTF_8),hmac(bytes).getBytes(StandardCharsets.UTF_8))){
                    reply(exchange,403,"{\"approved\":false,\"error\":\"INVALID_SIGNATURE\"}");return;
                }
                String data=new String(bytes,StandardCharsets.UTF_8);
                String src=stringField(data,"source_region"),dst=stringField(data,"dest_region"),tx=stringField(data,"transaction_id");
                long amount=amountField(data);
                boolean approved=amount>0&&!tx.isBlank()&&Set.of("af","eu","as","na","sa","oc").contains(src)&&Set.of("af","eu","as","na","sa","oc").contains(dst);
                reply(exchange,200,"{\"approved\":"+approved+",\"technology\":\"Java21\",\"format\":\"JSON\",\"integrity\":\"HMAC-SHA256\"}");
            }catch(Exception e){reply(exchange,400,"{\"approved\":false,\"error\":\"INVALID_JSON\"}");}
        });
        server.createContext("/health",ex->reply(ex,200,"{\"status\":\"ok\"}"));
        server.start();System.out.println("GlobalScale Legacy Java HTTPS/mTLS ready on 8090");
    }
}
