import * as express from "express";
import { fileFetchController } from "../controllers/FileFetchController";

class MainRoutes {
    public router: express.Router = express.Router();

    constructor() {
        this.config();
    }

    private config(): void {

        this.router.get("/loadfiles/", fileFetchController.load);

        /*
        this.router.get("/*", (req: express.Request, res: express.Response) => {
            fileFetchController.root(req, res);
        });
        */
    }
}

export const mainRoutes = new MainRoutes().router;