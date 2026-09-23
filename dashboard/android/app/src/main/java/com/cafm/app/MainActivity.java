package com.cafm.app;

import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        WebView webView = getBridge().getWebView();
        WebSettings settings = webView.getSettings();

        settings.setDomStorageEnabled(true);

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);
    }

    @Override
    public void onStop() {
        super.onStop();

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.flush();

        String cookies = cookieManager.getCookie("http://192.168.0.172:8003");
        android.util.Log.d("CAFM_COOKIES", "Cookies: " + cookies);
    }
}