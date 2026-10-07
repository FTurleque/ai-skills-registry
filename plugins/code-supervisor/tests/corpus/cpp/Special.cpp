class Widget {
public:
    Widget(const Widget&) = delete;
    virtual void run() = 0;
    Widget& operator=(const Widget&) = default;
    Widget(int size) = default;
    void draw(int width) {
        render(width);
    }
};
