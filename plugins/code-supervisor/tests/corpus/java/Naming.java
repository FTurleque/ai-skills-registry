package demo;

import java.util.List;
import java.util.Map;
import java.util.Set;

public class Naming {
    private String tmp;
    private int cnt;
    private int usr;
    private double amount1;
    private double amount2;
    private int q;

    public void process(Object obj, String s1, int val) {
        int x1 = 1;
        String data = "a";
        List<String> list1 = null;
        String ab = "b";
        for (int i = 0; i < 3; i++) {
            int z = i;
        }
    }

    public boolean getValue() {
        return true;
    }

    public boolean computeTotal(int a, int b) {
        return a > b;
    }

    public void getItems() {
        System.out.println("x");
    }

    public String getName() {
        String current = tmp;
        if (current == null) {
            current = "default";
        }
        saveAll(current);
        cnt = cnt + 1;
        return current;
    }

    public void Calculer_total() {
    }

    public void doit() {
    }

    public void handle() {
    }

    public int calcul1() {
        return 1;
    }

    public int setCount(int total) {
        cnt = total;
        usr = total;
        amount1 = total;
        amount2 = total;
        return cnt;
    }
}
