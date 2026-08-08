package com.barbermove.app;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebView;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.BridgeWebViewClient;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class MainActivity extends BridgeActivity {
    private static final String TAG = "BarberMoveCrash";
    private static final String CRASH_ENDPOINT =
        "https://projetobarbearia-production.up.railway.app/api/v1/notificacoes/frontend-crash";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // WebView nao tem DownloadListener por padrao: navegar para um .apk
        // (ex.: botao "Atualizar agora") nao baixa nada e trava a tela.
        // Repassa esses downloads para o navegador/gerenciador de downloads
        // do sistema, que sabe lidar com o instalador do APK.
        getBridge().getWebView().setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        });

        // Crashes nativos (Java/Kotlin) fecham o app sem deixar rastro nenhum
        // no JS - nem os handlers de window.onerror veem isso. Reporta pro
        // mesmo endpoint de diagnostico antes de deixar o app morrer.
        final Thread.UncaughtExceptionHandler previousHandler = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
            reportNativeCrash("uncaught-exception", throwable);
            if (previousHandler != null) {
                previousHandler.uncaughtException(thread, throwable);
            }
        });

        // Se o processo do WebView (renderer) morrer - ex.: OOM, crash nativo
        // de um plugin - o comportamento padrao e o app inteiro fechar. Aqui
        // so adicionamos o report em cima do BridgeWebViewClient original do
        // Capacitor (nao substituir por um WebViewClient generico - isso
        // quebra a ponte JS<->nativo e derruba o app na hora).
        getBridge()
            .getWebView()
            .setWebViewClient(
                new BridgeWebViewClient(getBridge()) {
                    @Override
                    public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                        reportNativeCrash(
                            "webview-render-process-gone",
                            new Exception("didCrash=" + detail.didCrash() + " rendererPriorityAtExit=" + detail.rendererPriorityAtExit())
                        );
                        return super.onRenderProcessGone(view, detail);
                    }
                }
            );
    }

    private void reportNativeCrash(String contexto, Throwable throwable) {
        new Thread(() -> {
            HttpURLConnection conn = null;
            try {
                StringWriter sw = new StringWriter();
                throwable.printStackTrace(new PrintWriter(sw));
                String stack = sw.toString();
                Log.e(TAG, "[" + contexto + "] " + throwable, throwable);

                String json = "{"
                    + "\"origem\":\"frontend\","
                    + "\"contexto\":\"native-" + contexto + "\","
                    + "\"mensagem\":" + jsonString(String.valueOf(throwable.getMessage())) + ","
                    + "\"stack\":" + jsonString(stack)
                    + "}";

                URL url = new URL(CRASH_ENDPOINT);
                conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(3000);
                conn.setDoOutput(true);
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(json.getBytes(StandardCharsets.UTF_8));
                }
                conn.getResponseCode();
            } catch (Throwable reportError) {
                Log.e(TAG, "Falha ao reportar crash nativo", reportError);
            } finally {
                if (conn != null) {
                    conn.disconnect();
                }
            }
        }).start();

        try {
            Thread.sleep(1500);
        } catch (InterruptedException ignored) {
            Thread.currentThread().interrupt();
        }
    }

    private static String jsonString(String value) {
        if (value == null) return "null";
        String truncated = value.substring(0, Math.min(value.length(), 2000));
        String escaped = truncated
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "");
        return "\"" + escaped + "\"";
    }
}
