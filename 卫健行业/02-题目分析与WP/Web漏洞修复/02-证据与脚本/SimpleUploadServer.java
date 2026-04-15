import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.Locale;
import java.util.concurrent.Executors;

public class SimpleUploadServer {
    private static final Path UPLOAD_DIR = Paths.get("/opt/app/upload").normalize();
    private static final byte[] INDEX_BYTES = (
            "<form action=\"/doUpload\" method=\"post\" enctype=\"multipart/form-data\" id=\"form\">\n" +
            "    <label for=\"file\">文件: </label>\n" +
            "    <input type=\"file\" name=\"file\" id=\"file\"><br>\n" +
            "    <input type=\"submit\" name=\"submit\" value=\"提交\">\n" +
            "</form>"
    ).getBytes(StandardCharsets.UTF_8);

    public static void main(String[] args) throws Exception {
        Files.createDirectories(UPLOAD_DIR);
        HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);
        server.createContext("/", new RootHandler());
        server.createContext("/doUpload", new UploadHandler());
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();
        System.out.println("SimpleUploadServer started on 8080");
    }

    static class RootHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                send(exchange, 405, "Method Not Allowed", "text/plain;charset=UTF-8");
                return;
            }
            send(exchange, 200, INDEX_BYTES, "text/html;charset=UTF-8");
        }
    }

    static class UploadHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                send(exchange, 405, "Method Not Allowed", "text/plain;charset=UTF-8");
                return;
            }
            try {
                Headers headers = exchange.getRequestHeaders();
                String contentType = headers.getFirst("Content-Type");
                if (contentType == null || !contentType.contains("multipart/form-data") || !contentType.contains("boundary=")) {
                    send(exchange, 200, "nonono", "text/plain;charset=UTF-8");
                    return;
                }
                String boundary = contentType.substring(contentType.indexOf("boundary=") + 9).trim();
                if (boundary.startsWith("\"") && boundary.endsWith("\"") && boundary.length() >= 2) {
                    boundary = boundary.substring(1, boundary.length() - 1);
                }
                MultipartPart part = extractFilePart(readAll(exchange.getRequestBody()), boundary);
                if (part == null || part.fileName == null || part.fileName.trim().isEmpty()) {
                    send(exchange, 200, "nonono", "text/plain;charset=UTF-8");
                    return;
                }

                String normalized = part.fileName.replace('\\', '/');
                String baseName = normalized;
                int slash = normalized.lastIndexOf('/');
                if (slash >= 0) {
                    baseName = normalized.substring(slash + 1);
                }
                if (baseName.isEmpty()) {
                    send(exchange, 200, "nonono", "text/plain;charset=UTF-8");
                    return;
                }
                if (!normalized.equals(baseName) || normalized.contains("..")) {
                    send(exchange, 200, "nonono", "text/plain;charset=UTF-8");
                    return;
                }
                String lower = baseName.toLowerCase(Locale.ROOT);
                if (!lower.endsWith(".jpg")) {
                    send(exchange, 200, "nonono", "text/plain;charset=UTF-8");
                    return;
                }
                if (baseName.contains("..") || baseName.contains("/") || baseName.contains("\\")) {
                    send(exchange, 200, "nonono", "text/plain;charset=UTF-8");
                    return;
                }

                Path target = UPLOAD_DIR.resolve(baseName).normalize();
                if (!target.startsWith(UPLOAD_DIR)) {
                    send(exchange, 200, "nonono", "text/plain;charset=UTF-8");
                    return;
                }
                Files.createDirectories(UPLOAD_DIR);
                Files.write(target, part.data);
                send(exchange, 200, target.toString(), "text/plain;charset=UTF-8");
            } catch (Exception e) {
                send(exchange, 200, "nonono", "text/plain;charset=UTF-8");
            }
        }
    }

    static class MultipartPart {
        String fileName;
        byte[] data;
    }

    static MultipartPart extractFilePart(byte[] body, String boundary) {
        byte[] boundaryBytes = ("--" + boundary).getBytes(StandardCharsets.ISO_8859_1);
        int first = indexOf(body, boundaryBytes, 0);
        if (first < 0) return null;
        int second = indexOf(body, boundaryBytes, first + boundaryBytes.length);
        if (second < 0) return null;

        int headerStart = first + boundaryBytes.length;
        if (match(body, headerStart, new byte[]{'\r','\n'})) headerStart += 2;
        int headerEnd = indexOf(body, new byte[]{'\r','\n','\r','\n'}, headerStart);
        if (headerEnd < 0) return null;
        String headers = new String(body, headerStart, headerEnd - headerStart, StandardCharsets.ISO_8859_1);
        if (!headers.contains("name=\"file\"")) return null;

        String fileName = null;
        int fn = headers.indexOf("filename=\"");
        if (fn >= 0) {
            int start = fn + 10;
            int end = headers.indexOf('"', start);
            if (end > start) fileName = headers.substring(start, end);
        }

        int dataStart = headerEnd + 4;
        int dataEnd = second;
        if (dataEnd >= 2 && body[dataEnd - 2] == '\r' && body[dataEnd - 1] == '\n') {
            dataEnd -= 2;
        }
        MultipartPart part = new MultipartPart();
        part.fileName = fileName;
        int len = Math.max(0, dataEnd - dataStart);
        part.data = new byte[len];
        System.arraycopy(body, dataStart, part.data, 0, len);
        return part;
    }

    static boolean match(byte[] data, int offset, byte[] pat) {
        if (offset + pat.length > data.length) return false;
        for (int i = 0; i < pat.length; i++) {
            if (data[offset + i] != pat[i]) return false;
        }
        return true;
    }

    static int indexOf(byte[] data, byte[] pat, int start) {
        outer:
        for (int i = Math.max(0, start); i <= data.length - pat.length; i++) {
            for (int j = 0; j < pat.length; j++) {
                if (data[i + j] != pat[j]) continue outer;
            }
            return i;
        }
        return -1;
    }

    static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = in.read(buf)) != -1) {
            out.write(buf, 0, n);
        }
        return out.toByteArray();
    }

    static void send(HttpExchange exchange, int code, String body, String contentType) throws IOException {
        send(exchange, code, body.getBytes(StandardCharsets.UTF_8), contentType);
    }

    static void send(HttpExchange exchange, int code, byte[] body, String contentType) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", contentType);
        exchange.sendResponseHeaders(code, body.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(body);
        }
    }
}
